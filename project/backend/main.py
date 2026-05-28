"""
主 API 服务 — FastAPI
三个界面共用的后端接口
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(__file__))

from database import get_db, init_db, seed_demo_data
from scraper import run_scraper, get_resource_stats
from delivery import process_delivery, batch_process_pending, create_order, set_delivery_rule
from scheduler import start_scheduler, get_scheduler_status, trigger_scrape

# ─── 初始化 ───
app = FastAPI(title="资源管理平台 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录（前端页面）
STATIC_DIR = os.path.join(os.path.dirname(__file__), '..')


@app.on_event("startup")
def startup():
    init_db()
    seed_demo_data()
    try:
        start_scheduler()
    except Exception as e:
        print(f"[Main] 定时任务启动失败（不影响API）: {e}")


# ─── 前端页面路由 ───
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))

@app.get("/aggregator.html")
def serve_aggregator():
    return FileResponse(os.path.join(STATIC_DIR, 'aggregator.html'))

@app.get("/organizer.html")
def serve_organizer():
    return FileResponse(os.path.join(STATIC_DIR, 'organizer.html'))

@app.get("/dashboard.html")
def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, 'dashboard.html'))


# ═══════════════════════════════════════
# 界面一：资源聚合 API
# ═══════════════════════════════════════

@app.get("/api/resources")
def list_resources(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str = "",
    search: str = "",
):
    """获取资源列表（分页/筛选/搜索）"""
    conn = get_db()
    cur = conn.cursor()

    where = ["status = 'active'"]
    params = []

    if category and category != "全部":
        where.append("category = ?")
        params.append(category)

    if search:
        where.append("(name LIKE ? OR description LIKE ? OR tags LIKE ?)")
        params.extend([f"%{search}%"] * 3)

    where_sql = " AND ".join(where)
    total = cur.execute(f"SELECT COUNT(*) FROM resources WHERE {where_sql}", params).fetchone()[0]

    offset = (page - 1) * size
    rows = cur.execute(
        f"SELECT * FROM resources WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [size, offset]
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "data": [dict(r) for r in rows],
    }


@app.get("/api/resources/categories")
def list_categories():
    """获取所有分类及其数量"""
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT category, COUNT(*) as cnt FROM resources WHERE status='active' GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    conn.close()
    return [{"name": r[0], "count": r[1]} for r in rows]


@app.get("/api/resources/stats")
def resource_stats():
    """资源统计概览"""
    conn = get_db()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    cats = cur.execute("SELECT COUNT(DISTINCT category) FROM resources").fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    today_new = cur.execute(
        "SELECT COUNT(*) FROM resources WHERE date(created_at) = ?", (today,)
    ).fetchone()[0]
    conn.close()
    return {"total": total, "categories": cats, "today_new": today_new}


@app.get("/api/resources/{resource_id}")
def get_resource(resource_id: int):
    """获取单个资源详情"""
    conn = get_db()
    row = conn.execute("SELECT * FROM resources WHERE id = ?", (resource_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "资源不存在")
    return dict(row)


@app.post("/api/scrape")
def trigger_scrape_api():
    """手动触发爬虫"""
    result = run_scraper()
    return result


# ═══════════════════════════════════════
# 界面二：资源整理 API
# ═══════════════════════════════════════

class TaskCreate(BaseModel):
    title: str
    category: str = ""
    priority: str = "中"
    pan_link: str = ""
    notes: str = ""

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    notes: Optional[str] = None


@app.get("/api/tasks")
def list_tasks(status: str = ""):
    """获取整理任务列表"""
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/tasks")
def create_task_api(task: TaskCreate):
    """创建整理任务"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, category, priority, pan_link, notes) VALUES (?, ?, ?, ?, ?)",
        (task.title, task.category, task.priority, task.pan_link, task.notes)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "id": task_id}


@app.put("/api/tasks/{task_id}")
def update_task_api(task_id: int, task: TaskUpdate):
    """更新整理任务"""
    conn = get_db()
    updates = []
    params = []
    for field, value in task.dict(exclude_none=True).items():
        updates.append(f"{field} = ?")
        params.append(value)
    if not updates:
        raise HTTPException(400, "没有要更新的字段")
    updates.append("updated_at = datetime('now','localtime')")
    params.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"success": True}


@app.delete("/api/tasks/{task_id}")
def delete_task_api(task_id: int):
    """删除整理任务"""
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"success": True}


@app.get("/api/tasks/stats")
def task_stats():
    """任务统计"""
    conn = get_db()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = cur.execute("SELECT COUNT(*) FROM tasks WHERE status='已完成'").fetchone()[0]
    progress = cur.execute("SELECT COUNT(*) FROM tasks WHERE status='进行中'").fetchone()[0]
    pending = cur.execute("SELECT COUNT(*) FROM tasks WHERE status='待开始'").fetchone()[0]
    conn.close()
    return {"total": total, "done": done, "in_progress": progress, "pending": pending}


# ═══════════════════════════════════════
# 界面三：电商销售 API
# ═══════════════════════════════════════

class ProductCreate(BaseModel):
    title: str
    category: str = ""
    price: float = 0
    platform: str = "淘宝"
    pan_link: str = ""

class OrderCreate(BaseModel):
    product_id: int
    platform: str = "淘宝"
    buyer_name: str = ""


@app.get("/api/products")
def list_products(platform: str = ""):
    """获取商品列表"""
    conn = get_db()
    if platform:
        rows = conn.execute("SELECT * FROM products WHERE platform = ? ORDER BY created_at DESC", (platform,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/products")
def create_product_api(product: ProductCreate):
    """创建商品"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (title, category, price, platform, pan_link) VALUES (?, ?, ?, ?, ?)",
        (product.title, product.category, product.price, product.platform, product.pan_link)
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "id": pid}


@app.get("/api/orders")
def list_orders(platform: str = "", status: str = ""):
    """获取订单列表"""
    conn = get_db()
    query = "SELECT o.*, p.title as product_title FROM orders o LEFT JOIN products p ON o.product_id = p.id WHERE 1=1"
    params = []
    if platform:
        query += " AND o.platform = ?"
        params.append(platform)
    if status:
        query += " AND o.status = ?"
        params.append(status)
    query += " ORDER BY o.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/orders")
def create_order_api(order: OrderCreate):
    """创建订单并自动发货"""
    result = create_order(order.product_id, order.platform, order.buyer_name)
    return result


@app.get("/api/finance")
def list_finance(type: str = "", days: int = 30):
    """获取财务流水"""
    conn = get_db()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = "SELECT * FROM finance WHERE created_at >= ?"
    params = [since]
    if type:
        query += " AND type = ?"
        params.append(type)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/finance/summary")
def finance_summary():
    """财务汇总"""
    conn = get_db()
    cur = conn.cursor()

    # 今日收入
    today = datetime.now().strftime("%Y-%m-%d")
    today_income = cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM finance WHERE type='收入' AND date(created_at) = ?", (today,)
    ).fetchone()[0]

    # 本月收入
    month_start = datetime.now().strftime("%Y-%m-01")
    month_income = cur.execute(
        "SELECT COALESCE(SUM(amount),0) FROM finance WHERE type='收入' AND created_at >= ?", (month_start,)
    ).fetchone()[0]

    # 本月支出
    month_expense = cur.execute(
        "SELECT COALESCE(SUM(ABS(amount)),0) FROM finance WHERE type='支出' AND created_at >= ?", (month_start,)
    ).fetchone()[0]

    # 今日订单
    today_orders = cur.execute(
        "SELECT COUNT(*) FROM orders WHERE date(created_at) = ?", (today,)
    ).fetchone()[0]

    # 累计客户
    total_customers = cur.execute("SELECT COUNT(DISTINCT buyer_id) FROM orders").fetchone()[0]

    # 平台收入分布
    platform_income = cur.execute(
        "SELECT platform, SUM(amount) as total FROM finance WHERE type='收入' AND created_at >= ? GROUP BY platform",
        (month_start,)
    ).fetchall()

    # 品类销售
    category_sales = cur.execute(
        "SELECT p.category, COUNT(*) as cnt FROM orders o JOIN products p ON o.product_id=p.id WHERE o.status='已完成' GROUP BY p.category ORDER BY cnt DESC LIMIT 5"
    ).fetchall()

    conn.close()

    return {
        "today_income": round(today_income, 2),
        "month_income": round(month_income, 2),
        "month_expense": round(month_expense, 2),
        "month_profit": round(month_income - month_expense, 2),
        "today_orders": today_orders,
        "total_customers": total_customers,
        "platform_income": [{"platform": p[0], "amount": round(p[1], 2)} for p in platform_income],
        "category_sales": [{"category": c[0], "count": c[1]} for c in category_sales],
    }


@app.get("/api/finance/daily")
def daily_revenue(days: int = 30):
    """每日收入趋势"""
    conn = get_db()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT date(created_at) as day, SUM(amount) as total
           FROM finance WHERE type='收入' AND created_at >= ?
           GROUP BY date(created_at) ORDER BY day""",
        (since,)
    ).fetchall()
    conn.close()
    return [{"date": r[0], "amount": round(r[1], 2)} for r in rows]


@app.get("/api/shops")
def list_shops():
    """获取店铺列表"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM shops ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════
# 自动发货 API
# ═══════════════════════════════════════

@app.post("/api/delivery/{order_no}")
def deliver_order(order_no: str):
    """手动触发发货"""
    result = process_delivery(order_no)
    return result


@app.post("/api/delivery/batch")
def batch_delivery():
    """批量处理待发货"""
    results = batch_process_pending()
    return {"results": results, "delivered": sum(1 for r in results if r.get("success"))}


@app.post("/api/delivery/rules")
def set_rule(product_id: int, platform: str, content: str, auto: bool = True):
    """设置发货规则"""
    return set_delivery_rule(product_id, platform, content, auto)


# ═══════════════════════════════════════
# 系统 API
# ═══════════════════════════════════════

@app.get("/api/scheduler")
def scheduler_status():
    """定时任务状态"""
    return get_scheduler_status()


@app.post("/api/scheduler/scrape")
def manual_scrape():
    """手动触发爬取"""
    return trigger_scrape()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ─── 挂载静态文件（CSS/JS等） ───
app.mount("/css", StaticFiles(directory=os.path.join(STATIC_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(STATIC_DIR, "js")), name="js")


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  资源管理平台 API 服务")
    print("  http://localhost:8000")
    print("  http://localhost:8000/docs  (API文档)")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
