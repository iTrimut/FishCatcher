# FishCatcher — 全对话记录

> 从零到一构建闭环资源管理销售平台的完整过程

---

## 第一轮：需求提出

**用户：**
我有几个需求，并且需求还得形成闭环：
1. 网址需要每一周爬取数据
2. 整理到我的网盘
3. 把网盘的东西按照类别打包到闲鱼进行售卖
4. 售卖的东西会在销售看板查看
5. 钱款会自动流入我的支付宝账户
6. 能够通过飞书看到整个流程图
7. 销售看板需要留出飞书账号进行关联，方便登陆退出进行更换
8. 销售看板需要设置网盘账号，方便登陆退出进行更换

**Claude：** 提出了一系列澄清问题。

**用户回答：**
- 服务器端定时跑（需要解决 Shadowsocks 代理问题）
- 自动转存到百度网盘，更新数据库
- 平台生成好商品标题/描述/定价，用户复制去闲鱼发布
- 买家下单后平台自动发货（百度网盘链接）
- 飞书只要一个地方填 Webhook 地址/群机器人 Token
- "登陆退出进行更换"是指支持切换不同的百度网盘账号
- 发货完成后催卖家确认收货

---

## 第二轮：规划与实施

Claude 制定了 4 阶段实施计划：

### Phase 1: 基础设施
- 百度网盘写入能力（create_folder, transfer_share, create_share）
- 多账号管理（BaiduPanManager）
- 飞书通知模块
- 代理配置（Shadowsocks SOCKS5）

### Phase 2: 深度爬取 + 自动转存
- 重写爬虫为深度爬取（首页→分类→详情页→入库）
- 自动转存到百度网盘（按分类建文件夹）

### Phase 3: 商品自动生成 + 增强发货
- 按分类聚合资源生成商品
- 闲鱼文案生成
- 增强发货（独立分享链接 + 催确认收货）

### Phase 4: 看板重写
- dashboard.html 用真实 API 数据
- 新增设置面板（百度网盘/飞书/爬取/收款码）

---

## 第三轮：Phase 1 实施

### 1.1 百度网盘写入能力

重写了 `project/backend/baidu_pan.py`：
- 添加 `_api_post()` 方法（镜像 `_api_get`，用 requests.post）
- `create_folder(path)` — 创建分类文件夹
- `resolve_share(share_url)` — 解析分享链接获取 shareid/fsid_list
- `transfer_share(share_url, save_path)` — 转存分享文件到自己网盘
- `create_share(fsids, password)` — 创建分享链接用于发货

### 1.2 多账号百度网盘管理

- 新建 `BaiduPanManager` 类，管理多个 `BaiduPanClient` 实例
- Token 文件改为 `data/baidu_tokens/{account_id}.json`
- API：GET/POST/DELETE /api/baidu/accounts，POST /api/baidu/accounts/switch

### 1.3 飞书 Webhook 模块

新建 `project/backend/feishu.py`：
- `send_feishu_message(webhook_url, title, content_lines)` — 发送飞书卡片消息
- `notify_crawl_report()` / `notify_new_order()` / `notify_daily_summary()`

### 1.4 代理配置

`project/backend/config.py` 添加：
```python
SHADOWSOCKS_PROXY = "socks5h://164.92.75.99:8388"
```

---

## 第四轮：Phase 2 实施

### 2.1 深度爬虫

重写 `project/backend/scraper.py`：
- 使用 SOCKS5 代理
- `parse_homepage(html)` — 发现分类链接
- `parse_category_page(html, category_name)` — 提取资源
- `scrape_detail_page(url)` — 跟随详情页提取百度网盘链接+提取码
- `run_deep_scrape()` — 全流程：首页→分类→详情页→入库
- `smart_category(name, base_cat)` — 智能分类映射（2024-2027年考试类型）

### 2.2 自动转存

新建 `project/backend/auto_save.py`：
- `run_auto_save()` — 查询未转存资源→按分类建文件夹→逐个转存→更新DB→飞书报告

### 2.3 定时任务

更新 `project/backend/scheduler.py`：
- 每周日凌晨3点深度爬取
- 凌晨4点自动转存
- 每5分钟订单同步

---

## 第五轮：Phase 3 实施

### 3.1 商品自动生成

新建 `project/backend/product_gen.py`：
- `generate_products()` — 按分类聚合资源生成商品（标题/描述/定价）
- `generate_xianyu_listings()` — 生成闲鱼可复制文案
- `PRICE_MAP` — 分类定价策略

### 3.2 增强发货

更新 `project/backend/delivery.py`：
- `_generate_share_link()` — 为每个买家生成独立分享链接
- `process_delivery()` — 发货后飞书通知
- `check_unconfirmed_orders()` — 24h未确认催收货

---

## 第六轮：Phase 4 实施

### 4.1 看板重写

完全重写 `project/dashboard.html`：
- KPI 卡片（收入/订单/资源/转化率）
- 收入趋势图（Chart.js 折线图）
- 平台占比图（饼图）
- 订单表（实时数据）
- 品类销售TOP5（柱状图）
- 自动刷新（60秒）
- 设置面板：百度网盘账号管理、飞书配置、爬取设置、收款码配置

### 4.2 聚合站和整理站

- `project/aggregator.html` — 对接 /api/resources，支持搜索/分类筛选/分页
- `project/organizer.html` — 对接 /api/tasks，支持创建/更新/删除任务

---

## 第七轮：数据库增强

更新 `project/backend/database.py`：
- resources 表新增：saved_to_pan, my_pan_link
- orders 表新增：share_link, confirm_reminded
- 新表：settings（键值配置）, crawl_logs（爬取历史）
- 幂等迁移（ALTER TABLE ADD COLUMN with try/except）

---

## 第八轮：飞书开放平台集成

用户提供了飞书开放平台应用凭证：
- App ID: (已配置到 .env)
- App Secret: (已配置到 .env)

重写 `project/backend/feishu.py`：
- 支持应用机器人发消息（tenant_access_token）
- `get_tenant_token()` — 获取 token 并缓存
- `get_chat_list()` — 获取机器人所在群列表
- `send_app_message(chat_id, title, content_lines)` — 通过应用发卡片消息
- `send_feishu_message()` — 统一接口，优先应用机器人，回退 Webhook

新增 API：
- GET /api/feishu/chat-list — 获取群列表
- POST /api/feishu/test — 测试发送（不再依赖 webhook_url）

---

## 第九轮：百度网盘授权

用户提供了百度网盘凭证：
- AppID: (已配置到 .env)
- AppKey: (已配置到 .env)
- Secretkey: (已配置到 .env)

更新了 config.py 和 baidu_pan.py 中的 API Key。

---

## 第十轮：连通测试

- 服务器启动成功（端口 8000）
- /api/feishu/config — 正常返回
- /api/feishu/chat-list — 正常返回
- 用户提供了 chat_id（已配置到 feishu_config.json）
- POST /api/feishu/test — **发送成功！** 飞书群收到测试消息

---

## 最终状态

### 已完成
- [x] 百度网盘多账号管理 + 写入能力
- [x] 飞书开放平台应用消息（已连通）
- [x] 深度爬虫（代理支持）
- [x] 自动转存网盘
- [x] 商品自动生成 + 闲鱼文案
- [x] 增强发货（独立链接 + 催确认）
- [x] 定时任务（每周日爬取+转存）
- [x] Dashboard 看板（真实数据 + 设置面板）
- [x] 资源聚合站（搜索/筛选/分页）
- [x] 任务整理站（CRUD）

### 待完成
- [ ] 百度网盘 OAuth 授权（用户需在浏览器完成）
- [ ] 云服务器部署（24/7 运行）

### 闭环流程
```
每周日凌晨3点 → 深度爬取 lasee.net → 入库
        ↓
凌晨4点 → 自动转存到百度网盘（按分类建文件夹）
        ↓
自动生成商品 → 生成闲鱼上架文案（用户复制发布）
        ↓
买家下单 → 自动发货（百度网盘链接） → 飞书通知
        ↓
发货后24h → 催确认收货
```

### 文件结构
```
project/
├── index.html              # 主入口导航页
├── aggregator.html         # 资源聚合导航站
├── organizer.html          # 资源整理服务
├── dashboard.html          # 销售看板 + 设置面板
└── backend/
    ├── main.py             # FastAPI 主服务（40+ API 端点）
    ├── database.py         # SQLite（9张表）
    ├── baidu_pan.py        # 百度网盘多账号管理
    ├── feishu.py           # 飞书通知（应用+Webhook）
    ├── scraper.py          # 深度爬虫（代理支持）
    ├── auto_save.py        # 自动转存网盘
    ├── product_gen.py      # 商品自动生成 + 闲鱼文案
    ├── delivery.py         # 自动发货引擎
    ├── payment.py          # 个人收款码支付
    ├── scheduler.py        # 定时任务
    ├── config.py           # 配置
    └── start.sh            # 一键启动
```
