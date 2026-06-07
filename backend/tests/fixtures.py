"""pytest fixtures for backend tests

方案：使用 SQLite 文件数据库（非 :memory:），因为 FastAPI TestClient
通过 lifespan 启动时会调用 init_db()，需要持久化的数据库文件。
"""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def test_db():
    """创建 SQLite 临时文件数据库，供模型测试和 API 测试共享"""
    import database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # 使用临时文件（非 :memory:），因为 lifespan 会从不同连接创建表
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"

    database.DATABASE_URL = db_url
    database._is_postgres = False
    database.engine = create_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
        # 某些 SQLite 版本不支持 RETURNING 子句
        # 如果 Python 的 sqlite3 库版本 < 3.35，需要禁用 RETURNING
    )
    database.SessionLocal = sessionmaker(
        bind=database.engine, autoflush=False, autocommit=False
    )
    database.Base.metadata.create_all(bind=database.engine)

    db = database.SessionLocal()
    yield db
    db.close()
    database.Base.metadata.drop_all(bind=database.engine)
    database.engine.dispose()
    os.unlink(db_path)


@pytest.fixture(scope="function")
def test_client(test_db):
    """创建测试用 FastAPI TestClient

    关键：必须在 lifespan 启动前设置好 database 连接，
    让 FastAPI app 的 init_db() 使用我们创建的数据库。
    """
    from main import app
    from database import get_db as original_get_db

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[original_get_db] = override_get_db

    # 手动调用 init_db（绕过 lifespan）
    from database import init_db
    init_db()

    with TestClient(app) as client:
        yield client

    if original_get_db in app.dependency_overrides:
        del app.dependency_overrides[original_get_db]
