#!/bin/bash
# PostgreSQL 自动备份脚本
# 用法: ./deploy/backup.sh
# 建议配置 crontab 每天凌晨执行: 0 2 * * * /path/to/deploy/backup.sh

set -euo pipefail

# 从环境变量读取数据库连接
DB_URL="${DATABASE_URL:-}"
if [ -z "$DB_URL" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

# 备份目录
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

# 备份文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ozon_analytics_$TIMESTAMP.sql.gz"

# 保留天数
RETENTION_DAYS="${RETENTION_DAYS:-30}"

echo "Starting backup: $BACKUP_FILE"

# 解析 DATABASE_URL
# 格式: postgresql://user:password@host:port/dbname
DB_HOST=$(echo "$DB_URL" | sed -E 's|.*@([^:]+).*|\1|')
DB_PORT=$(echo "$DB_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_NAME=$(echo "$DB_URL" | sed -E 's|.*/([^?]+).*|\1|')
DB_USER=$(echo "$DB_URL" | sed -E 's|postgresql://([^:]+):.*|\1|')
DB_PASS=$(echo "$DB_URL" | sed -E 's|postgresql://[^:]+:([^@]+)@.*|\1|')

# 执行备份
PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

# 检查备份文件
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup completed: $BACKUP_FILE ($SIZE)"

    # 清理过期备份
    find "$BACKUP_DIR" -name "ozon_analytics_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "Cleaned backups older than $RETENTION_DAYS days"
else
    echo "ERROR: Backup file not created"
    exit 1
fi
