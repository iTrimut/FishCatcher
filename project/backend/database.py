"""数据库管理 — SQLite，零配置，开箱即用"""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'resources.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    # 资源表 — 爬取的所有资源
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '未分类',
            description TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            pan_link TEXT DEFAULT '',
            file_size TEXT DEFAULT '',
            download_count INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 整理任务表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT '',
            priority TEXT DEFAULT '中',
            status TEXT DEFAULT '待开始',
            progress INTEGER DEFAULT 0,
            pan_link TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 商品表 — 对接淘宝/闲鱼
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT '',
            price REAL DEFAULT 0,
            platform TEXT DEFAULT '淘宝',
            product_url TEXT DEFAULT '',
            pan_link TEXT DEFAULT '',
            sales INTEGER DEFAULT 0,
            status TEXT DEFAULT '在售',
            resource_ids TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 订单表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            product_id INTEGER,
            platform TEXT DEFAULT '淘宝',
            buyer_id TEXT DEFAULT '',
            buyer_name TEXT DEFAULT '',
            amount REAL DEFAULT 0,
            status TEXT DEFAULT '待支付',
            delivered_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # 财务流水表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS finance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT '收入',
            amount REAL NOT NULL DEFAULT 0,
            category TEXT DEFAULT '',
            description TEXT DEFAULT '',
            platform TEXT DEFAULT '',
            order_no TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 店铺渠道表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            shop_url TEXT DEFAULT '',
            status TEXT DEFAULT '营业中',
            product_count INTEGER DEFAULT 0,
            monthly_sales INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # 自动发货规则表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            platform TEXT DEFAULT '淘宝',
            delivery_type TEXT DEFAULT '网盘链接',
            content TEXT DEFAULT '',
            auto_deliver INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] 数据库初始化完成: {DB_PATH}")


def seed_demo_data():
    """插入演示数据，方便预览"""
    conn = get_db()
    cur = conn.cursor()

    # 检查是否已有数据
    if cur.execute("SELECT COUNT(*) FROM resources").fetchone()[0] > 0:
        conn.close()
        return

    # 插入示例资源
    demo_resources = [
        ("Figma 设计资源合集 2026", "设计素材", "500+高质量Figma组件库", "https://lasee.net/figma", "https://pan.baidu.com/s/demo1", "2.3 GB", 1520),
        ("React + Next.js 全栈模板", "源码", "完整全栈项目模板", "https://lasee.net/react", "https://pan.baidu.com/s/demo2", "850 MB", 892),
        ("Premiere Pro 转场特效包", "视频模板", "200+专业转场效果", "https://lasee.net/pr", "https://pan.baidu.com/s/demo3", "4.1 GB", 2341),
        ("Python 机器学习教程", "文档教程", "从入门到实战", "https://lasee.net/python", "https://pan.baidu.com/s/demo4", "12 GB", 3102),
        ("Adobe 全家桶 2026", "工具软件", "PS/AI/AE全套工具", "https://lasee.net/adobe", "https://pan.baidu.com/s/demo5", "18 GB", 5620),
        ("1000+ 免费商用字体", "字体", "思源/普惠体/站酷系列", "https://lasee.net/fonts", "https://pan.baidu.com/s/demo6", "3.2 GB", 4210),
        ("商业计划书 PPT 50套", "PPT模板", "高端商务风格", "https://lasee.net/ppt", "https://pan.baidu.com/s/demo7", "1.5 GB", 1890),
        ("3D 建模素材库 Blender", "设计素材", "500+高质量3D模型", "https://lasee.net/3d", "https://pan.baidu.com/s/demo8", "15 GB", 980),
    ]
    cur.executemany(
        "INSERT INTO resources (name,category,description,source_url,pan_link,file_size,download_count) VALUES (?,?,?,?,?,?,?)",
        demo_resources
    )

    # 插入示例任务
    demo_tasks = [
        ("Figma素材包整理", "设计素材", "高", "已完成", 100, "", "已分类并添加标签"),
        ("Python教程分类", "文档教程", "中", "进行中", 65, "", "正在整理章节结构"),
        ("PR转场包质量筛选", "视频模板", "高", "进行中", 40, "", "筛选高质量转场"),
        ("字体版权审核", "字体", "高", "待开始", 0, "", "待确认版权状态"),
        ("Vue项目源码标注", "源码", "低", "已完成", 100, "", "已添加注释和说明"),
    ]
    cur.executemany(
        "INSERT INTO tasks (title,category,priority,status,progress,pan_link,notes) VALUES (?,?,?,?,?,?,?)",
        demo_tasks
    )

    # 插入示例商品
    demo_products = [
        ("Figma设计资源合集", "设计素材", 9.9, "淘宝", "", "https://pan.baidu.com/s/demo1", 342, "在售"),
        ("Python机器学习教程", "文档教程", 15.0, "闲鱼", "", "https://pan.baidu.com/s/demo4", 567, "在售"),
        ("PR转场特效包", "视频模板", 19.9, "淘宝", "", "https://pan.baidu.com/s/demo3", 289, "在售"),
        ("商用字体合集", "字体", 5.9, "闲鱼", "", "https://pan.baidu.com/s/demo6", 890, "在售"),
        ("PPT模板50套", "PPT模板", 12.0, "淘宝", "", "https://pan.baidu.com/s/demo7", 156, "在售"),
    ]
    cur.executemany(
        "INSERT INTO products (title,category,price,platform,product_url,pan_link,sales,status) VALUES (?,?,?,?,?,?,?,?)",
        demo_products
    )

    # 插入示例订单
    demo_orders = [
        ("TB20260529001", 1, "淘宝", "buyer_001", "用户A", 9.9, "已完成", "2026-05-29 10:00:00"),
        ("XY20260529001", 2, "闲鱼", "buyer_002", "用户B", 15.0, "已完成", "2026-05-29 10:15:00"),
        ("TB20260529002", 3, "淘宝", "buyer_003", "用户C", 19.9, "已完成", "2026-05-29 11:00:00"),
        ("XY20260529002", 4, "闲鱼", "buyer_004", "用户D", 5.9, "待支付", "2026-05-29 11:30:00"),
        ("TB20260529003", 5, "淘宝", "buyer_005", "用户E", 12.0, "已完成", "2026-05-29 12:00:00"),
        ("TB20260529004", 1, "淘宝", "buyer_006", "用户F", 9.9, "已完成", "2026-05-29 13:00:00"),
        ("XY20260529003", 2, "闲鱼", "buyer_007", "用户G", 15.0, "已退款", "2026-05-29 14:00:00"),
    ]
    for o in demo_orders:
        cur.execute(
            "INSERT INTO orders (order_no,product_id,platform,buyer_id,buyer_name,amount,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
            o
        )

    # 插入财务流水
    demo_finance = [
        ("收入", 9.9, "淘宝销售", "Figma设计资源合集", "淘宝", "TB20260529001"),
        ("收入", 15.0, "闲鱼销售", "Python机器学习教程", "闲鱼", "XY20260529001"),
        ("收入", 19.9, "淘宝销售", "PR转场特效包", "淘宝", "TB20260529002"),
        ("收入", 12.0, "淘宝销售", "PPT模板50套", "淘宝", "TB20260529003"),
        ("收入", 9.9, "淘宝销售", "Figma设计资源合集", "淘宝", "TB20260529004"),
        ("支出", -1.5, "平台手续费", "淘宝扣点", "淘宝", ""),
        ("支出", -0.8, "平台手续费", "闲鱼扣点", "闲鱼", ""),
        ("支出", -300, "运营成本", "百度网盘会员", "", ""),
    ]
    cur.executemany(
        "INSERT INTO finance (type,amount,category,description,platform,order_no) VALUES (?,?,?,?,?,?)",
        demo_finance
    )

    # 插入店铺
    demo_shops = [
        ("资源精选馆", "淘宝", "", "营业中", 86, 342),
        ("精选资源铺", "闲鱼", "", "营业中", 124, 567),
        ("资源宝", "微信", "", "维护中", 52, 89),
    ]
    cur.executemany(
        "INSERT INTO shops (name,platform,shop_url,status,product_count,monthly_sales) VALUES (?,?,?,?,?,?)",
        demo_shops
    )

    conn.commit()
    conn.close()
    print("[DB] 演示数据插入完成")


if __name__ == "__main__":
    init_db()
    seed_demo_data()
