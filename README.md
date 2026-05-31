<div align="center">

# FishCatcher

**从资源爬取到闲鱼变现的一站式闭环销售平台**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/iTrimut/FishCatcher?style=social)](https://github.com/iTrimut/FishCatcher)

简体中文 | [English](#english)

</div>

---

## 项目简介

FishCatcher 是一个**全自动闭环资源销售系统**，将网上免费共享的考试资料、电子书、视频课程等资源，经过自动抓取、分类整理、转存网盘后，在闲鱼等平台进行售卖变现。

整个流程**全自动运行**，无需人工干预：

```
每周自动爬取 → 智能分类 → 转存百度网盘 → 生成闲鱼商品文案
      ↓                                          ↓
  飞书通知                                 用户一键复制发布到闲鱼
      ↓                                          ↓
  销售看板 ← 自动发货（独立网盘链接） ← 买家下单付款
                                              ↓
                                    24h后催确认收货
```

## 功能特性

### 核心能力

- **深度爬虫** — 从资源站首页出发，自动发现分类→遍历列表→进入详情页→提取网盘链接和提取码
- **智能分类** — 自动识别考试类型和年份（2024-2027），支持一建、二建、考公、教资等 14 种考试
- **自动转存** — 按分类在百度网盘创建文件夹，逐条转存资源，0.5s 间隔防限流
- **商品生成** — 按分类聚合资源，自动生成标题、描述、定价，一键生成闲鱼上架文案
- **自动发货** — 买家下单后自动创建独立分享链接并发货，支持飞书实时通知
- **催确认收货** — 发货 24 小时后自动提醒买家确认

### 平台功能

- **销售看板** — KPI 卡片、收入趋势图、平台占比饼图、订单管理、品类 TOP5
- **资源聚合站** — 搜索、分类筛选、分页浏览，支持一键转存
- **任务管理** — 创建/更新/删除整理任务，状态追踪
- **设置面板** — 百度网盘多账号管理、飞书配置、爬取设置、收款码配置

### 外部集成

- **百度网盘** — 多账号管理、OAuth2 授权、文件夹创建、转存分享、创建分享链接
- **飞书** — 应用机器人发卡片消息 + Webhook 备选，支持爬取报告/新订单/每日汇总/转存报告
- **SOCKS5 代理** — 服务器端爬取通过 Shadowsocks 代理访问目标站

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                    前端页面                        │
│  index.html │ aggregator.html │ organizer.html │ dashboard.html │
└────────────────────────┬────────────────────────┘
                         │ HTTP API
┌────────────────────────┴────────────────────────┐
│                  FastAPI 后端                      │
│  main.py — 40+ API 端点                           │
├─────────────────────────────────────────────────┤
│ scraper  │ auto_save │ product_gen │ delivery    │
│ 爬虫      │ 自动转存   │ 商品生成     │ 自动发货    │
├─────────────────────────────────────────────────┤
│ baidu_pan │ feishu   │ scheduler  │ database    │
│ 百度网盘   │ 飞书通知   │ 定时任务     │ SQLite     │
└─────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| Python | 3.9+ | 3.11+ |
| 内存 | 512 MB | 1 GB+ |
| 存储 | 100 MB | 1 GB+（含数据） |
| 网络 | 需要外网访问 | SOCKS5 代理 |

### 安装部署

**1. 克隆项目**
```bash
git clone https://github.com/iTrimut/FishCatcher.git
cd FishCatcher
```

**2. 创建虚拟环境**
```bash
cd project/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. 配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 填入你的密钥
```

需要配置的密钥：

| 变量 | 说明 | 获取方式 |
|------|------|---------|
| `BAIDU_APP_ID` | 百度网盘 AppID | [百度开放平台](https://openapi.baidu.com) |
| `BAIDU_APP_KEY` | 百度网盘 AppKey | 同上 |
| `BAIDU_SECRET_KEY` | 百度网盘 SecretKey | 同上 |
| `FEISHU_APP_ID` | 飞书应用 AppID | [飞书开放平台](https://open.feishu.cn) |
| `FEISHU_APP_SECRET` | 飞书应用 AppSecret | 同上 |
| `SHADOWSOCKS_PROXY` | SOCKS5 代理地址 | 自行搭建或购买 |

**4. 启动服务**
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**5. 访问**
- 主入口：http://localhost:8000/
- 销售看板：http://localhost:8000/dashboard.html
- 资源聚合：http://localhost:8000/aggregator.html
- 任务管理：http://localhost:8000/organizer.html
- API 文档：http://localhost:8000/docs

### Docker 部署（可选）
```bash
docker-compose up -d
```

## 文件结构

```
FishCatcher/
├── .claude/commands/
│   └── fishcatcher.md        # Claude Code Skill
├── .env.example              # 环境变量模板
├── conversation-log.md       # 完整构建过程记录
├── project/
│   ├── index.html            # 主入口导航
│   ├── aggregator.html       # 资源聚合站
│   ├── organizer.html        # 任务管理站
│   ├── dashboard.html        # 销售看板 + 设置面板
│   └── backend/
│       ├── main.py           # FastAPI 主服务（40+ 端点）
│       ├── database.py       # SQLite 数据库（9 张表）
│       ├── baidu_pan.py      # 百度网盘多账号管理
│       ├── feishu.py         # 飞书通知（应用+Webhook）
│       ├── scraper.py        # 深度爬虫（SOCKS5 代理）
│       ├── auto_save.py      # 自动转存到网盘
│       ├── product_gen.py    # 商品自动生成 + 闲鱼文案
│       ├── delivery.py       # 自动发货引擎
│       ├── payment.py        # 个人收款码支付
│       ├── scheduler.py      # 定时任务调度
│       ├── config.py         # 配置管理
│       └── requirements.txt  # Python 依赖
└── data/                     # 运行时数据（不提交）
    ├── resources.db          # SQLite 数据库
    ├── feishu_config.json    # 飞书配置
    └── baidu_tokens/         # 百度网盘 Token
```

## 定时任务

| 时间 | 任务 | 说明 |
|------|------|------|
| 每周日 03:00 | 深度爬取 | 从 lasee.net 抓取最新资源入库 |
| 每周日 04:00 | 自动转存 | 将新资源转存到百度网盘 |
| 每 5 分钟 | 订单同步 | 检查新订单并自动发货 |

## 飞书通知

系统会在以下事件发生时推送飞书消息：

- **爬取完成** — 新增资源数量、分类统计、耗时
- **新订单** — 订单号、商品、金额、平台
- **每日汇总** — 当日收入、订单数、品类 TOP5
- **转存完成** — 成功/失败数量、分类统计
- **催确认收货** — 超时未确认的订单提醒

## API 端点

<details>
<summary>点击展开完整 API 列表</summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/resources` | 资源列表（分页/搜索/筛选） |
| GET | `/api/resources/stats` | 资源统计 |
| GET | `/api/resources/categories` | 分类列表 |
| GET/POST | `/api/tasks` | 任务 CRUD |
| GET/POST | `/api/orders` | 订单管理 |
| POST | `/api/orders/{no}/remind-confirm` | 催确认收货 |
| GET/POST | `/api/finance` | 财务记录 |
| GET | `/api/finance/summary` | 财务汇总 |
| GET | `/api/finance/daily` | 每日收入 |
| GET/POST | `/api/shops` | 店铺管理 |
| GET/POST/DELETE | `/api/baidu/accounts` | 百度网盘账号 |
| POST | `/api/baidu/accounts/switch` | 切换活跃账号 |
| GET/POST | `/api/feishu/config` | 飞书配置 |
| GET | `/api/feishu/chat-list` | 飞书群列表 |
| POST | `/api/feishu/test` | 测试飞书消息 |
| POST | `/api/auto-save` | 手动触发转存 |
| POST | `/api/products/auto-generate` | 生成商品 |
| GET | `/api/products/xianyu-listings` | 闲鱼文案列表 |
| GET | `/api/dashboard/overview` | 看板总览 |
| GET | `/api/crawl-history` | 爬取历史 |

</details>

## 数据库

9 张 SQLite 表：

| 表名 | 说明 |
|------|------|
| `resources` | 资源库（名称/分类/链接/转存状态） |
| `tasks` | 整理任务 |
| `products` | 商品（标题/描述/定价/关联资源） |
| `orders` | 订单（状态/发货/分享链接） |
| `finance` | 财务记录（收入/支出） |
| `shops` | 店铺信息 |
| `delivery_rules` | 发货规则 |
| `settings` | 键值配置 |
| `crawl_logs` | 爬取历史日志 |

## 常见问题

<details>
<summary><b>百度网盘授权失败？</b></summary>

确保 AppID、AppKey、SecretKey 正确配置在 `.env` 中。授权链接需要在浏览器中打开完成 OAuth 流程。
</details>

<details>
<summary><b>飞书消息发送失败？</b></summary>

1. 确认飞书应用已发布并获得 `im:message:create` 权限
2. 确认机器人已添加到目标群
3. 确认 `chat_id` 配置正确（通过"获取群列表"获取）
</details>

<details>
<summary><b>爬虫抓不到数据？</b></summary>

1. 确认 SOCKS5 代理可用：`curl --proxy socks5h://your-proxy:port https://lasee.net`
2. 目标站可能有反爬，系统内置了重试机制
3. 检查 `crawl_logs` 表查看错误详情
</details>

<details>
<summary><b>定时任务没有执行？</b></summary>

确认服务持续运行中。APScheduler 依赖进程存活，电脑关机或服务停止后任务不会执行。建议部署到云服务器。
</details>

## 许可证

[MIT License](LICENSE)

---

<div align="center">
<b>如果这个项目对你有帮助，请给一个 Star 支持一下！</b>
</div>
