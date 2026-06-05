# Ozon Seller API 参考文档 (v2.1)

> 基于 Ozon Seller API Postman Collection 整理  
> 整理日期: 2026-06-04  
> 官方文档: https://docs.ozon.ru/api/seller/

---

## 目录

1. [基础信息](#基础信息)
2. [属性与特征](#1-属性与特征-атрибуты-и-характеристики-ozon)
3. [商品上传与更新](#2-商品上传与更新-загрузка-и-обновление-товаров)
4. [商品条码](#3-商品条码-штрихкоды-товаров)
5. [价格与库存](#4-价格与库存-цены-и-остатки-товаров)
6. [促销活动](#5-促销活动-акции)
7. [定价策略](#6-定价策略-стратегии-ценообразования)
8. [品牌认证](#7-品牌认证-сертификаты-брендов)
9. [质量证书](#8-质量证书-сертификаты-качества)
10. [仓库与配送方式](#9-仓库与配送方式-склады)
11. [FBS/rFBS 订单处理](#10-fbsrfbs-订单处理-обработка-заказов-fbs-и-rfbs)
12. [FBO 配送](#11-fbo-配送-доставка-fbo)
13. [FBS 配送与标记码](#12-fbs-配送与标记码)
14. [rFBS 配送](#13-rfbs-配送-доставка-rfbs)
15. [通行证管理](#14-通行证管理-пропуски)
16. [退货管理](#15-退货管理)
17. [订单取消](#16-订单取消-отмены-заказов)
18. [买家聊天](#17-买家聊天-чаты-с-покупателями)
19. [发票/运单](#18-发票运单-накладные)
20. [报告与财务](#19-报告与财务)
21. [卖家评级](#20-卖家评级-рейтинг-продавца)
22. [Beta 功能](#21-beta-功能-β)

---

## 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `https://api-seller.ozon.ru` |
| 请求方式 | 绝大多数为 POST（少数 GET） |
| 必填 Header | `Client-Id`: 卖家客户端ID / `Content-Type`: `application/json` |
| API Key 方式 | 通过 Header `Api-Key` 传递 |
| 数据格式 | JSON |

### 核心概念

- **offer_id**: 卖家系统中的商品货号（自定义）
- **product_id**: Ozon 系统中的商品ID（系统分配）
- **SKU**: Ozon 仓库中的商品唯一标识
- **FBO**: Fulfillment by Ozon — Ozon 仓储配送模式
- **FBS**: Fulfillment by Seller — 卖家自发货模式
- **rFBS**: Real FBS — 卖家使用自有物流发货模式
- **posting_number**: 订单号
- **description_category_id**: 商品所属类目ID
- **type_id**: 商品类型ID

---

## 1. 属性与特征 (Атрибуты и характеристики Ozon)

### 1.1 获取类目树

```
POST /v1/description-category/tree
```

- **说明**: 获取商品类目和类型的树形结构。只能在末级类目下创建商品。
- **参数**:
  - `language`: 语言，默认 `"DEFAULT"`

---

### 1.2 获取类目特征列表

```
POST /v1/description-category/attribute
```

- **说明**: 获取指定类目和类型的商品属性/特征。如果 `dictionary_id` 为 `0`，则该属性无嵌套字典；否则需通过 attribute/values 获取字典值。
- **参数**:
  - `description_category_id`: 类目ID
  - `type_id`: 类型ID
  - `language`: 语言

---

### 1.3 获取特征字典值

```
POST /v1/description-category/attribute/values
```

- **说明**: 获取某个特征的字典值列表。用于下拉选择属性值。
- **参数**:
  - `attribute_id`: 属性ID
  - `description_category_id`: 类目ID
  - `type_id`: 类型ID
  - `language`: 语言
  - `last_value_id`: 分页起始值ID（默认0）
  - `limit`: 每页数量（最大100）

---

### 1.4 搜索特征字典值

```
POST /v1/description-category/attribute/values/search
```

- **说明**: 按值搜索特征字典。
- **参数**:
  - `attribute_id`: 属性ID
  - `description_category_id`: 类目ID
  - `type_id`: 类型ID
  - `value`: 搜索关键词
  - `limit`: 每页数量

---

## 2. 商品上传与更新 (Загрузка и обновление товаров)

### 2.1 创建/更新商品

```
POST /v3/product/import
```

- **说明**: 最核心的商品创建与更新接口。每请求最多 100 个商品。每日创建/更新有配额限制。
- **关键参数** (每个 item):
  - `offer_id` *必填*: 卖家货号
  - `name` *必填*: 商品名称
  - `description_category_id` *必填*: 类目ID
  - `type_id`: 类型ID
  - `price` *必填*: 售价（字符串）
  - `old_price`: 原价（划线价）
  - `vat` *必填*: 增值税率，如 `"0.1"`, `"0.2"`, `"0"`
  - `currency_code`: 货币代码，默认 `"RUB"`；CNY 为 `"CNY"`
  - `barcode`: 条形码
  - `attributes`: 商品属性数组，每个属性含 `id`, `values`（含 `dictionary_value_id` 和 `value`）
  - `depth`, `width`, `height`: 长宽高 **必填且不能为0**
  - `dimension_unit`: 尺寸单位，`"mm"`
  - `weight`: 重量 **必填且不能为0**
  - `weight_unit`: 重量单位，`"g"`
  - `images`: 图片URL数组（至多15张，第一张为主图）
  - `images360`: 360全景图片数组
  - `color_image`: 营销颜色图
  - `primary_image`: 主图
  - `complex_attributes`: 复杂属性数组（如多值属性）
  - `pdf_list`: PDF文档

> ⚠️ 限制: 每日创建和更新商品有配额限制，查询方法: `/v4/product/info/limit`；超限报错 `item_limit_exceeded`。

---

### 2.2 查询商品导入状态

```
POST /v1/product/import/info
```

- **说明**: 查询商品创建任务的处理状态。
- **参数**: `task_id`: 任务ID（来自 `/v3/product/import` 的返回值）

---

### 2.3 按 Ozon ID 创建商品

```
POST /v1/product/import-by-sku
```

- **说明**: 按已有 Ozon SKU 创建商品。只能创建不能更新。数量不限。
- **参数**: `items[]`: SKU + offer_id + name + price + old_price + currency_code + vat

---

### 2.4 更新商品属性

```
POST /v1/product/attributes/update
```

- **说明**: 单独更新商品的特征属性。
- **参数**: `items[]`: offer_id + attributes[]

---

### 2.5 上传/更新商品图片

```
POST /v1/product/pictures/import
```

- **说明**: 上传商品图片。**每次调用会覆盖全部现有图片，务必传入完整的图片列表**。图片按数组顺序排列，首张为主图。最多15张。图片URL需指向公开云存储，格式JPG/PNG。
- **参数**:
  - `product_id`: 商品ID
  - `images`: 图片URL数组
  - `color_image`: 颜色图URL
  - `images360`: 360图URL数组

---

### 2.6 检查图片上传状态

```
POST /v2/product/pictures/info
```

- **参数**: `product_id[]`: 商品ID数组

---

### 2.7 商品列表 (v2)

```
POST /v2/product/list
```

- **说明**: 获取商品列表，支持分页。
- **参数**:
  - `filter.offer_id[]`, `filter.product_id[]`: 筛选条件
  - `filter.visibility`: `"ALL"` / `"VISIBLE"` 等
  - `last_id`: 分页游标
  - `limit`: 每页数量（最大100）

---

### 2.8 商品列表 (v3)

```
POST /v3/product/list
```

- **说明**: v3 版本商品列表。

---

### 2.9 商品详细列表

```
POST /v3/product/info/list
```

- **说明**: 获取商品详细信息。
- **参数**: `offer_id[]` / `product_id[]` / `sku[]`（三选一或多选）

---

### 2.10 获取商品内容评分

```
POST /v1/product/rating-by-sku
```

- **说明**: 获取商品内容评级及优化建议。
- **参数**: `skus[]`: SKU数组

---

### 2.11 获取商品特征描述 (v3)

```
POST /v3/products/info/attributes
```

- **说明**: 按商品ID获取特征描述。支持按 `offer_id` 或 `product_id` 查询。
- **参数**: `filter.product_id[]` / `filter.offer_id[]`, `filter.visibility`, `limit`, `last_id`, `sort_dir`

---

### 2.12 获取商品特征描述 (v4)

```
POST /v4/products/info/attributes
```

- **说明**: v4版本，支持多维度筛选。
- **参数**: `filter.product_id[]`, `filter.offer_id[]`, `filter.sku[]`, `filter.visibility`, `limit`, `sort_dir`

---

### 2.13 获取商品描述

```
POST /v1/product/info/description
```

- **参数**: `offer_id` / `product_id`

---

### 2.14 查询上传配额

```
POST /v4/product/info/limit
```

- **说明**: 查询每日创建/更新商品的限额以及总品类限额。
- **参数**: 空 JSON `{}`

---

### 2.15 修改卖家货号

```
POST /v1/product/update/offer-id
```

- **说明**: 修改商品绑定的 `offer_id`。建议每次不超过250个。
- **参数**: `update_offer_id[]`: `offer_id`（旧） + `new_offer_id`（新）

---

### 2.16 归档商品

```
POST /v1/product/archive
```

- **参数**: `product_id[]`: 商品ID数组

---

### 2.17 取消归档

```
POST /v1/product/unarchive
```

- **参数**: `product_id[]`

---

### 2.18 删除商品

```
POST /v2/products/delete
```

- **说明**: 从归档中删除无SKU的商品。
- **参数**: `products[]`: offer_id

---

### 2.19 上传数字商品激活码 & 2.20 查询激活码状态

```
POST /v1/product/upload_digital_codes
POST /v1/product/upload_digital_codes/info
```

- **说明**: 数字商品/服务类需上传激活码。

---

### 2.21 商品订阅数查询

```
POST /v1/product/info/subscription
```

- **说明**: 获取点击"到货通知"的用户数。
- **参数**: `skus[]`

---

### 2.22 获取关联SKU

```
POST /v1/product/related-sku/get
```

- **说明**: 获取FBS/FBO SKU的统一映射。最多200个SKU/请求。
- **参数**: `skus[]`

---

## 3. 商品条码 (Штрихкоды товаров)

### 3.1 绑定条码

```
POST /v1/barcode/add
```

- **说明**: 将已有条码绑定到商品。**频率限制**: 20次/分钟，每次最多100个商品，每个商品最多100个条码。
- **参数**: `barcodes[]`: barcode + sku

---

### 3.2 生成条码

```
POST /v1/barcode/generate
```

- **说明**: 为无条码商品自动生成条码。**频率限制**: 20次/分钟，每次最多100个商品。
- **参数**: `product_ids[]`

---

## 4. 价格与库存 (Цены и остатки товаров)

### 4.1 更新库存 (v1 已弃用)

```
POST /v1/product/import/stocks
```

- **说明**: ⚠️ 即将停用，迁移到 `/v2/products/stocks`。每次最多100个商品，最多80次请求/分钟。**同一仓库同一商品 2 分钟内只能更新一次**，否则报 `TOO_MANY_REQUESTS`。
- **参数**: `stocks[]`: offer_id / product_id + stock

---

### 4.2 更新库存 (v2 推荐)

```
POST /v2/products/stocks
```

- **说明**: 更新各仓库的商品库存。**必须在商品状态变为 `price_sent` 后才能更新**。
- **参数**: `stocks[]`: offer_id / product_id + stock + warehouse_id

---

### 4.3 查询库存信息

```
POST /v3/product/info/stocks
```

- **说明**: 查询各仓库库存（在售数 + 预留数）。
- **参数**: `filter.product_id[]`, `filter.visibility`, `last_id`, `limit`

---

### 4.4 查询FBS/rFBS仓库库存

```
POST /v1/product/info/stocks-by-warehouse/fbs
```

- **参数**: `sku[]`

---

### 4.5 更新价格

```
POST /v1/product/import/prices
```

- **说明**: 批量更新价格，**每次最多1000个商品**。
- **参数** (每个 price):
  - `offer_id` / `product_id`
  - `price`: 售价
  - `old_price`: 原价（设为 `"0"` 清空划线价）
  - `currency_code`: `"RUB"` 或 `"CNY"`
  - `min_price`: 最低价格
  - `min_price_for_auto_actions_enabled`: 是否启用自动参与活动的最低价
  - `vat`: 增值税率
  - `auto_action_enabled`: 是否启用自动参与活动（`"UNKNOWN"`）
  - `price_strategy_enabled`: 是否启用定价策略
  - `quant_size`: 批量数量

---

### 4.6 查询价格信息 (v5)

```
POST /v5/product/info/prices
```

- **说明**: 查询商品价格信息。每次最多1000个商品。
- **参数**: `filter.offer_id[]` / `filter.product_id[]`, `filter.visibility`, `cursor`, `limit`
- **注意**: 响应中的 `fbo_direct_flow_trans_max_amount` 和 `fbo_direct_flow_trans_min_amount` 尚在开发中，返回 `0`。

---

### 4.7 查询折价商品信息

```
POST /v1/product/info/discounted
```

- **说明**: 获取折价商品的折损状态和主商品SKU。
- **参数**: `discounted_skus[]`

---

### 4.8 设置折价商品折扣

```
POST /v1/product/update/discount
```

- **说明**: 为FBS折价商品设置折扣率。
- **参数**: `product_id`, `discount`

---

## 5. 促销活动 (Акции)

### 5.1 获取活动列表

```
GET /v1/actions
```

- **说明**: 获取可参与的促销活动列表。

---

### 5.2 获取活动可选商品

```
POST /v1/actions/candidates
```

- **参数**: `action_id`, `limit`, `offset`

---

### 5.3 获取已参与活动商品

```
POST /v1/actions/products
```

- **参数**: `action_id`, `limit`, `offset`

---

### 5.4 添加商品到活动

```
POST /v1/actions/products/activate
```

- **参数**: `action_id`, `products[]`: product_id + action_price + stock

---

### 5.5 从活动中移除商品

```
POST /v1/actions/products/deactivate
```

- **参数**: `action_id`, `product_ids[]`

---

### 5.6-5.9 Hot Sale 活动

```
POST /v1/actions/hotsales/list           # Hot Sale活动列表
POST /v1/actions/hotsales/products       # 参与Hot Sale的商品
POST /v1/actions/hotsales/activate       # 添加商品到Hot Sale
POST /v1/actions/hotsales/deactivate     # 从Hot Sale移除商品
```

---

### 5.10-5.12 折扣申请

```
POST /v1/actions/discounts-task/list    # 折扣申请列表 (status: NEW/SEEN)
POST /v1/actions/discounts-task/approve # 同意折扣申请
POST /v1/actions/discounts-task/decline # 拒绝折扣申请
```

---

## 6. 定价策略 (Стратегии ценообразования)

### 端点列表

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/pricing-strategy/competitors/list` | 竞争对手列表（相似的卖家） |
| POST | `/v1/pricing-strategy/list` | 策略列表 |
| POST | `/v1/pricing-strategy/create` | 创建策略（策略名 + 竞争对手 + 系数） |
| POST | `/v1/pricing-strategy/info` | 策略详情 |
| POST | `/v1/pricing-strategy/update` | 更新策略 |
| POST | `/v1/pricing-strategy/products/add` | 添加商品到策略 |
| POST | `/v1/pricing-strategy/strategy-ids-by-product-ids` | 按商品ID查策略ID |
| POST | `/v1/pricing-strategy/products/list` | 策略中的商品列表 |
| POST | `/v1/pricing-strategy/product/info` | 竞品价格信息 |
| POST | `/v1/pricing-strategy/products/delete` | 从策略移除商品 |
| POST | `/v1/pricing-strategy/status` | 启用/禁用策略 |
| POST | `/v1/pricing-strategy/delete` | 删除策略 |

---

## 7. 品牌认证 (Сертификаты брендов)

### 7.1 品牌认证列表

```
POST /v1/brand/company-certification/list
```

- **说明**: 获取需要提供品牌认证证书的品牌列表。列表会随品牌方要求动态变化。

---

## 8. 质量证书 (Сертификаты качества)

### 端点列表

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/v1/product/certificate/accordance-types` | 合规类型列表 (v1) |
| GET | `/v2/product/certificate/accordance-types/list` | 合规类型列表 (v2) |
| GET | `/v1/product/certificate/types` | 文档类型字典 |
| POST | `/v1/product/certification/list` | 需认证的类目列表 |
| POST | `/v1/product/certificate/create` | 创建证书（名称 + 编号 + 类型 + 签发日期 + 文件） |
| POST | `/v1/product/certificate/bind` | 绑定证书到商品 |
| POST | `/v1/product/certificate/delete` | 删除证书 |
| POST | `/v1/product/certificate/info` | 证书信息 |
| POST | `/v1/product/certificate/list` | 证书列表（可按offer_id, status, type筛） |
| POST | `/v1/product/certificate/product_status/list` | 商品绑定状态列表 |
| POST | `/v1/product/certificate/products/list` | 证书关联商品列表 |
| POST | `/v1/product/certificate/unbind` | 解绑商品与证书 |
| POST | `/v1/product/certificate/rejection_reasons/list` | 证书拒绝原因列表 |
| POST | `/v1/product/certificate/status/list` | 证书状态列表 |

---

## 9. 仓库与配送方式 (Склады)

### 9.1 仓库列表

```
POST /v1/warehouse/list
```

- **参数**: 空 JSON `{}`

---

### 9.2 配送方式列表

```
POST /v1/delivery-method/list
```

- **参数**: `filter.provider_id`, `filter.status`, `filter.warehouse_id`, `limit`, `offset`

---

## 10. FBS/rFBS 订单处理 (Обработка заказов FBS и rFBS)

### 10.1 待处理订单列表

```
POST /v3/posting/fbs/unfulfilled/list
```

- **说明**: 获取FBS未完成订单列表。支持按状态 `awaiting_packaging`（待打包）等筛选。
- **参数**: `dir`, `filter`（cutoff_from/to, delivery_method_id, provider_id, status, warehouse_id）, `limit`, `offset`, `with`（analytics_data, barcodes, financial_data, translit）

---

### 10.2 订单列表 (通用)

```
POST /v3/posting/fbs/list
```

- **参数**: `dir`, `filter`（since, status, to）, `limit`, `offset`

---

### 10.3 获取订单详情

```
POST /v3/posting/fbs/get
```

- **参数**: `posting_number`, `with`（analytics_data, barcodes, financial_data, product_exemplars, translit）

---

### 10.4 按条形码查询订单

```
POST /v2/posting/fbs/get-by-barcode
```

- **参数**: `barcode`

---

### 10.5 设置多箱数量

```
POST /v3/posting/multiboxqty/set
```

- **说明**: 设置订单分多个包裹发货的箱数。

---

### 10.6 修改订单商品

```
POST /v2/posting/fbs/product/change
```

- **说明**: 修改订单中商品的重量等参数。
- **参数**: `posting_number`, `items[]`（sku + weightReal[]）

---

### 10.7 FBS商品产地管理

```
POST /v2/posting/fbs/product/country/list   # 产地国别列表
POST /v2/posting/fbs/product/country/set    # 设置商品产地图
```

---

### 10.8 订单限制查询

```
POST /v1/posting/fbs/restrictions
```

---

### 10.9 包裹标签

```
POST /v2/posting/fbs/package-label           # 获取包裹标签
POST /v2/posting/fbs/package-label/create    # 创建包裹标签
POST /v1/posting/fbs/package-label/get       # 按task_id获取标签
```

---

### 10.10 订单取消

```
POST /v1/posting/fbs/cancel-reason            # 获取取消原因
POST /v2/posting/fbs/cancel-reason/list       # 取消原因列表
POST /v2/posting/fbs/product/cancel           # 取消订单中的部分商品
POST /v2/posting/fbs/cancel                   # 取消整个订单
```

---

### 10.11 仲裁/发货

```
POST /v2/posting/fbs/arbitration              # 发起仲裁
POST /v2/posting/fbs/awaiting-delivery        # 标记为待发货
POST /v1/posting/global/etgb                  # 全球ETGB
```

---

### 10.12 取件码验证

```
POST /v1/posting/fbs/pick-up-code/verify
```

---

### 10.13 未支付法人订单

```
POST /v1/posting/unpaid-legal/product/list
```

---

### 10.14 配送区域（Полигоны）

```
POST /v1/polygon/create     # 创建配送区域
POST /v1/polygon/bind       # 绑定配送区域
```

---

## 11. FBO 配送 (Доставка FBO)

### 端点列表

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v2/posting/fbo/list` | FBO订单列表 |
| POST | `/v2/posting/fbo/get` | FBO订单详情 |
| POST | `/v1/posting/fbo/cancel-reason/list` | FBO取消原因列表 |
| POST | `/v1/supply-order/status/counter` | 供应订单状态计数 |
| POST | `/v2/supply-order/list` | 供应订单列表 |
| POST | `/v2/supply-order/get` | 供应订单详情 |
| POST | `/v1/supply-order/bundle` | 打包供应订单 |
| POST | `/v1/supply-order/timeslot/get` | 获取时间段 |
| POST | `/v1/supply-order/timeslot/update` | 更新时间段 |
| POST | `/v1/supply-order/timeslot/status` | 时间段状态 |
| POST | `/v1/supply-order/pass/create` | 创建通行证 |
| POST | `/v1/supply-order/pass/status` | 通行证状态 |
| POST | `/v1/supplier/available_warehouses` | 可用仓库列表 |

---

## 12. FBS 配送与标记码

### 12.1 标记码管理

```
POST /v4/fbs/posting/product/exemplar/validate        # 验证标记码
POST /v5/fbs/posting/product/exemplar/set             # 设置标记码
POST /v4/fbs/posting/product/exemplar/status          # 标记码状态
POST /v5/fbs/posting/product/exemplar/create-or-get   # 创建或获取标记码
```

### 12.2 FBS 发货

```
POST /v4/posting/fbs/ship                             # 发货（整单）
POST /v4/posting/fbs/ship/package                     # 发货（按包裹）
```

### 12.3 运单管理

```
POST /v2/posting/fbs/act/create                       # 创建运单
POST /v2/posting/fbs/act/get-postings                 # 获取运单中的订单
POST /v2/posting/fbs/act/get-container-labels         # 获取容器标签
POST /v2/posting/fbs/act/get-barcode                  # 获取运单条码
POST /v2/posting/fbs/act/get-barcode/text             # 获取运单条码文本
POST /v2/posting/fbs/digital/act/check-status         # 数字运单状态
POST /v2/posting/fbs/act/get-pdf                      # 获取运单PDF
POST /v2/posting/fbs/act/list                         # 运单列表
POST /v2/posting/fbs/digital/act/get-pdf              # 获取数字运单PDF
POST /v2/posting/fbs/act/check-status                 # 运单状态
```

### 12.4 运输管理

```
POST /v1/carriage-available/list                      # 可用运输方式
POST /v1/carriage/get                                 # 运输详情
POST /v1/posting/fbs/split                            # 拆分订单
```

---

## 13. rFBS 配送 (Доставка rFBS)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v2/fbs/posting/tracking-number/set` | 设置物流单号 |
| POST | `/v2/fbs/posting/sent-by-seller` | 标记为卖家已发货 |
| POST | `/v2/fbs/posting/delivering` | 标记为运输中 |
| POST | `/v2/fbs/posting/last-mile` | 标记为最后一公里 |
| POST | `/v2/fbs/posting/delivered` | 标记为已送达 |
| POST | `/v1/posting/fbs/timeslot/change-restrictions` | 修改时间限制 |
| POST | `/v1/posting/fbs/timeslot/set` | 设置时间段 |
| POST | `/v1/posting/cutoff/set` | 设置截单时间 |

---

## 14. 通行证管理 (Пропуски)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/pass/list` | 通行证列表 |
| POST | `/v1/carriage/pass/create` | 创建运输通行证 |
| POST | `/v1/carriage/pass/update` | 更新运输通行证 |
| POST | `/v1/carriage/pass/delete` | 删除运输通行证 |
| POST | `/v1/return/pass/create` | 创建退货通行证 |
| POST | `/v1/return/pass/update` | 更新退货通行证 |
| POST | `/v1/return/pass/delete` | 删除退货通行证 |

---

## 15. 退货管理

### 15.1 FBO/FBS 退货

```
POST /v1/returns/list                                 # 退货列表
```

### 15.2 rFBS 退货

```
POST /v2/returns/rfbs/list                            # rFBS退货列表
POST /v2/returns/rfbs/get                             # rFBS退货详情
POST /v2/returns/rfbs/reject                          # 拒绝退货
POST /v2/returns/rfbs/compensate                      # 补偿
POST /v2/returns/rfbs/verify                          # 验证退货
POST /v2/returns/rfbs/receive-return                  # 接收退货
POST /v2/returns/rfbs/return-money                    # 退款
```

### 15.3 退货发货 (Возвратные отгрузки)

```
POST /v1/returns/company/fbs/info                     # FBS退货公司信息
POST /v1/return/giveout/is-enabled                    # 退货发货是否可用
POST /v1/return/giveout/list                          # 退货发货列表
POST /v1/return/giveout/info                          # 退货发货详情
POST /v1/return/giveout/barcode                       # 获取退货条码
POST /v1/return/giveout/get-pdf                       # 获取退货标签PDF
POST /v1/return/giveout/get-png                       # 获取退货标签PNG
POST /v1/return/giveout/barcode-reset                 # 重置退货条码
```

---

## 16. 订单取消 (Отмены заказов)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/conditional-cancellation/get` | 获取有条件取消详情 |
| POST | `/v1/conditional-cancellation/list` | 有条件取消列表 |
| POST | `/v1/conditional-cancellation/approve` | 同意有条件取消 |
| POST | `/v1/conditional-cancellation/reject` | 拒绝有条件取消 |

---

## 17. 买家聊天 (Чаты с покупателями)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/chat/send/message` | 发送消息 |
| POST | `/v1/chat/send/file` | 发送文件 |
| POST | `/v1/chat/start` | 发起聊天 |
| POST | `/v2/chat/list` | 聊天列表 |
| POST | `/v2/chat/history` | 聊天历史 |
| POST | `/v2/chat/read` | 标记已读 |

---

## 18. 发票/运单 (Накладные)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v2/invoice/create-or-update` | 创建或更新发票 |
| POST | `/v1/invoice/file/upload` | 上传发票文件 |
| POST | `/v2/invoice/get` | 获取发票 |
| POST | `/v1/invoice/delete` | 删除发票 |

---

## 19. 报告与财务

### 19.1 报告

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/report/info` | 报告状态信息 |
| POST | `/v1/report/list` | 报告列表 |
| POST | `/v1/report/products/create` | 创建商品报告 |
| POST | `/v2/report/returns/create` | 创建退货报告 |
| POST | `/v1/report/postings/create` | 创建订单报告 |
| POST | `/v1/report/discounted/create` | 创建折价商品报告 |
| POST | `/v1/report/warehouse/stock` | 仓库库存报告 |

### 19.2 分析报告

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/analytics/data` | 分析数据 |
| POST | `/v2/analytics/stock_on_warehouses` | 各仓库库存分析 |
| POST | `/v1/analytics/turnover/stocks` | 库存周转分析 |

### 19.3 财务报告

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/finance/cash-flow-statement/list` | 现金流量表 |
| POST | `/v2/finance/realization` | 销售实现报告 |
| POST | `/v3/finance/transaction/list` | 交易列表 |
| POST | `/v3/finance/transaction/totals` | 交易汇总 |

---

## 20. 卖家评级 (Рейтинг продавца)

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/rating/summary` | 评级摘要 |
| POST | `/v1/rating/history` | 评级历史 |

- **参数**: `date_from`, `date_to`, `ratings[]`, `with_premium_scores`

---

## 21. Beta 功能 (β)

### 21.1 其他方法

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/v1/analytics/manage/stocks` | 库存管理分析 |
| POST | `/v1/finance/document-b2b-sales` | B2B销售凭证 |
| POST | `/v1/finance/mutual-settlement` | 相互结算凭证 |
| POST | `/v4/product/info/attributes` | 商品属性(v4) |
| POST | `/v4/product/info/stocks` | 库存信息(v4) |
| POST | `/v2/product/certification/list` | 认证列表(v2) |

### 21.2 运输管理 (β)

```
POST /v1/carriage/create            # 创建运输
POST /v1/carriage/approve           # 批准运输
POST /v1/carriage/delivery/list     # 运输配送列表
POST /v1/carriage/set-postings      # 设置运输订单
POST /v1/carriage/cancel            # 取消运输
```

### 21.3 自动操作定时器

```
POST /v1/product/action/timer/update    # 更新定时器
POST /v1/product/action/timer/status    # 定时器状态
```

### 21.4 集群与FBO仓库

```
POST /v1/cluster/list                   # 集群列表
POST /v1/warehouse/fbo/list             # FBO仓库列表
```

### 21.5 FBO 供应申请 (β)

```
POST /v1/draft/create                   # 创建草稿
POST /v1/draft/create/info              # 草稿创建状态
POST /v1/draft/timeslot/info            # 草稿时间段
POST /v1/draft/supply/create            # 创建供应
POST /v1/supply/create/status           # 供应创建状态
```

### 21.6 批量/量子管理 (β)

```
POST /v1/product/quant/list             # 商品批量列表
POST /v1/product/quant/info             # 商品批量详情
POST /v1/quant/list                     # 批量列表
POST /v1/quant/get                      # 批量详情
POST /v1/quant/ship                     # 批量发货
POST /v1/quant/status                   # 批量状态
```

### 21.7 货位管理 (β)

```
POST /v1/cargoes/create                 # 创建货位
POST /v1/cargoes/create/info            # 货位创建状态
POST /v1/cargoes-label/create           # 创建货位标签
POST /v1/cargoes-label/get              # 获取货位标签
GET  /v1/cargoes-label/file/{file_guid} # 获取货位标签文件
```

### 21.8 评价管理 (β)

```
POST /v1/review/comment/create          # 创建回复
POST /v1/review/comment/delete          # 删除回复
POST /v1/review/comment/list            # 回复列表
POST /v1/review/change-status           # 修改评价状态
POST /v1/review/count                   # 评价计数
POST /v1/review/info                    # 评价详情
POST /v1/review/list                    # 评价列表
```

### 21.9 问答管理 (β)

```
POST /v1/question/answer/create         # 创建回答
POST /v1/question/answer/delete         # 删除回答
POST /v1/question/answer/list           # 回答列表
POST /v1/question/change_status         # 修改问题状态
POST /v1/question/count                 # 问题计数
POST /v1/question/info                  # 问题详情
POST /v1/question/list                  # 问题列表
POST /v1/question/top_sku               # 热门商品问题
```

---

## 附录: Python 调用 Ozon API 模版

```python
import requests
import json

# 配置
BASE_URL = "https://api-seller.ozon.ru"
CLIENT_ID = "your_client_id"
API_KEY = "your_api_key"

headers = {
    "Client-Id": CLIENT_ID,
    "Api-Key": API_KEY,
    "Content-Type": "application/json"
}


def ozon_post(endpoint: str, body: dict) -> dict:
    """通用 POST 请求"""
    url = f"{BASE_URL}{endpoint}"
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ====== 示例: 查询商品列表 ======
products = ozon_post("/v2/product/list", {
    "filter": {"visibility": "ALL"},
    "last_id": "",
    "limit": 100
})

# ====== 示例: 更新库存 ======
result = ozon_post("/v2/products/stocks", {
    "stocks": [
        {
            "offer_id": "PH11042",
            "product_id": 313455276,
            "stock": 100,
            "warehouse_id": 22142605386000
        }
    ]
})

# ====== 示例: 更新价格 ======
result = ozon_post("/v1/product/import/prices", {
    "prices": [
        {
            "offer_id": "136748",
            "price": "1448",
            "old_price": "0",
            "currency_code": "RUB",
            "vat": "0.1",
            "min_price": "800",
            "auto_action_enabled": "UNKNOWN"
        }
    ]
})

# ====== 示例: 获取订单列表 (FBS) ======
orders = ozon_post("/v3/posting/fbs/list", {
    "dir": "ASC",
    "filter": {
        "since": "2025-01-15T00:00:00.000Z",
        "to": "2025-01-25T00:00:00.000Z",
        "status": "awaiting_deliver"
    },
    "limit": 100,
    "offset": 0
})

# ====== 示例: 获取财务交易 ======
transactions = ozon_post("/v3/finance/transaction/list", {
    "filter": {
        "date": {
            "from": "2025-01-01T00:00:00.000Z",
            "to": "2025-01-31T23:59:59.000Z"
        },
        "transaction_type": "ALL"
    },
    "page": 1,
    "page_size": 100
})
```

---

## 附录: 实用注意事项

1. **库存更新频率限制**: 同一仓库同一商品每 2 分钟只能更新 1 次，超频返回 `TOO_MANY_REQUESTS`。
2. **价格更新**: 单次最多 1000 个商品。
3. **商品创建**: 单次最多 100 个商品，每日有配额，先查 `/v4/product/info/limit`。
4. **图片更新**: `/v1/product/pictures/import` 是全量覆盖，务必传入全部图片URL。
5. **类目树**: 只能在末级类目下创建商品。
6. **货币**: 默认 `RUB`，如使用人民币需传 `CNY` 且在后台设置中匹配。
7. **条形码**: 每分钟最多 20 次调用。
8. **商品状态**: 必须在 `price_sent` 之后才能更新库存。
