# FishCatcher — 闭环资源管理销售平台

> 一键构建从爬取到变现的全自动资源管理系统

## 项目概述

FishCatcher 是一个闭环资源管理销售平台，实现：

```
每周自动爬取 → 转存网盘 → 生成闲鱼商品 → 自动发货 → 飞书通知 → 催确认收货
```

## 技术栈

- **后端**: FastAPI (Python) + SQLite
- **前端**: 纯 HTML/CSS/JS (无框架)
- **API**: 百度网盘 Open API + 飞书开放平台
- **爬虫**: requests + BeautifulSoup4 + SOCKS5 代理
- **定时任务**: APScheduler
- **图表**: Chart.js

## 核心模块

### 1. 百度网盘管理 (`baidu_pan.py`)
- 多账号管理 (BaiduPanManager)
- 创建文件夹、转存分享、创建分享链接
- OAuth2 授权流程

### 2. 飞书通知 (`feishu.py`)
- 应用机器人发消息 (tenant_access_token)
- Webhook 备选方案
- 通知类型：爬取报告、新订单、每日汇总、转存报告

### 3. 深度爬虫 (`scraper.py`)
- 首页 → 分类 → 详情页 → 入库
- SOCKS5 代理支持
- 智能分类映射（年份+考试类型）

### 4. 自动转存 (`auto_save.py`)
- 查询未转存资源 → 按分类建文件夹 → 逐个转存
- 0.5s 间隔防限流

### 5. 商品生成 (`product_gen.py`)
- 按分类聚合资源生成商品
- 自动定价策略
- 闲鱼文案生成（可复制）

### 6. 自动发货 (`delivery.py`)
- 为每个买家生成独立分享链接
- 24h 未确认 → 催收货提醒

### 7. 定时调度 (`scheduler.py`)
- 每周日凌晨 3:00 深度爬取
- 凌晨 4:00 自动转存
- 每 5 分钟订单同步

## 文件结构

```
project/
├── index.html              # 主入口导航
├── aggregator.html         # 资源聚合站（搜索/筛选/分页）
├── organizer.html          # 任务管理站（CRUD）
├── dashboard.html          # 销售看板 + 设置面板
└── backend/
    ├── main.py             # FastAPI 主服务
    ├── database.py         # SQLite 数据库
    ├── baidu_pan.py        # 百度网盘多账号
    ├── feishu.py           # 飞书通知
    ├── scraper.py          # 深度爬虫
    ├── auto_save.py        # 自动转存
    ├── product_gen.py      # 商品生成
    ├── delivery.py         # 自动发货
    ├── payment.py          # 支付流程
    ├── scheduler.py        # 定时任务
    ├── config.py           # 配置
    └── start.sh            # 启动脚本
```

## 启动方式

```bash
cd project/backend
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

访问：
- http://localhost:8000/ — 主入口
- http://localhost:8000/dashboard.html — 看板
- http://localhost:8000/docs — API 文档

## 使用此 Skill

当用户提到以下关键词时，参考此文档：
- 资源管理、闲鱼卖货、自动发货
- 百度网盘转存、飞书通知
- 爬虫、定时任务、销售看板
- FishCatcher、闭环销售

## 对话记录

完整的构建过程记录在 `conversation-log.md` 中。
