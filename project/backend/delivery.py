"""自动发货引擎 — 根据订单自动发送网盘链接"""
import json
from datetime import datetime
from database import get_db


def process_delivery(order_no: str) -> dict:
    """处理单个订单的自动发货"""
    conn = get_db()
    cur = conn.cursor()

    # 查找订单
    order = cur.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
    if not order:
        conn.close()
        return {"success": False, "msg": "订单不存在"}

    if order["status"] == "已完成":
        conn.close()
        return {"success": False, "msg": "订单已发货"}

    if order["status"] != "待发货" and order["status"] != "已支付":
        # 如果是待支付状态，先标记为已支付
        if order["status"] == "待支付":
            cur.execute("UPDATE orders SET status = '已支付' WHERE order_no = ?", (order_no,))
            conn.commit()
        else:
            conn.close()
            return {"success": False, "msg": f"订单状态异常: {order['status']}"}

    # 查找商品对应的网盘链接
    product = cur.execute("SELECT * FROM products WHERE id = ?", (order["product_id"],)).fetchone()
    if not product:
        conn.close()
        return {"success": False, "msg": "商品不存在"}

    # 查找发货规则
    rule = cur.execute(
        "SELECT * FROM delivery_rules WHERE product_id = ? AND platform = ?",
        (order["product_id"], order["platform"])
    ).fetchone()

    if rule:
        delivery_content = rule["content"]
    else:
        # 默认使用商品的网盘链接
        delivery_content = f"""
【自动发货】
商品：{product['title']}
网盘链接：{product['pan_link']}
提取码：请联系客服获取

使用说明：
1. 点击链接进入百度网盘
2. 输入提取码
3. 保存到自己的网盘后下载

如有问题请联系客服，祝您使用愉快！
""".strip()

    # 更新订单状态
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "UPDATE orders SET status = '已完成', delivered_at = ? WHERE order_no = ?",
        (now, order_no)
    )

    # 更新商品销量
    cur.execute(
        "UPDATE products SET sales = sales + 1 WHERE id = ?",
        (order["product_id"],)
    )

    # 记录收入流水
    cur.execute(
        """INSERT INTO finance (type, amount, category, description, platform, order_no)
           VALUES ('收入', ?, '销售', ?, ?, ?)""",
        (order["amount"], product["title"], order["platform"], order_no)
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "order_no": order_no,
        "product": product["title"],
        "delivery_content": delivery_content,
        "delivered_at": now,
    }


def batch_process_pending() -> list:
    """批量处理所有待发货订单"""
    conn = get_db()
    cur = conn.cursor()
    pending_orders = cur.execute(
        "SELECT order_no FROM orders WHERE status IN ('待发货', '已支付')"
    ).fetchall()
    conn.close()

    results = []
    for row in pending_orders:
        result = process_delivery(row["order_no"])
        results.append(result)

    return results


def create_order(product_id: int, platform: str, buyer_name: str = "") -> dict:
    """创建新订单（模拟买家下单）"""
    conn = get_db()
    cur = conn.cursor()

    product = cur.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        conn.close()
        return {"success": False, "msg": "商品不存在"}

    # 生成订单号
    prefix = {"淘宝": "TB", "闲鱼": "XY", "微信": "WC"}.get(platform, "OT")
    today = datetime.now().strftime("%Y%m%d")
    count = cur.execute(
        "SELECT COUNT(*) FROM orders WHERE order_no LIKE ?", (f"{prefix}{today}%",)
    ).fetchone()[0]
    order_no = f"{prefix}{today}{count+1:03d}"

    cur.execute(
        """INSERT INTO orders (order_no, product_id, platform, buyer_name, amount, status)
           VALUES (?, ?, ?, ?, ?, '已支付')""",
        (order_no, product_id, platform, buyer_name, product["price"])
    )
    conn.commit()
    conn.close()

    # 自动发货
    delivery = process_delivery(order_no)

    return {
        "success": True,
        "order_no": order_no,
        "product": product["title"],
        "amount": product["price"],
        "delivery": delivery,
    }


def set_delivery_rule(product_id: int, platform: str, content: str, auto: bool = True) -> dict:
    """设置商品的自动发货规则"""
    conn = get_db()
    cur = conn.cursor()

    # 更新或插入
    existing = cur.execute(
        "SELECT id FROM delivery_rules WHERE product_id = ? AND platform = ?",
        (product_id, platform)
    ).fetchone()

    if existing:
        cur.execute(
            "UPDATE delivery_rules SET content = ?, auto_deliver = ? WHERE id = ?",
            (content, 1 if auto else 0, existing["id"])
        )
    else:
        cur.execute(
            "INSERT INTO delivery_rules (product_id, platform, content, auto_deliver) VALUES (?, ?, ?, ?)",
            (product_id, platform, content, 1 if auto else 0)
        )

    conn.commit()
    conn.close()
    return {"success": True, "msg": "发货规则已保存"}


if __name__ == "__main__":
    # 测试：创建一个订单并自动发货
    print("=== 测试自动发货 ===")
    result = create_order(1, "淘宝", "测试用户")
    print(json.dumps(result, ensure_ascii=False, indent=2))
