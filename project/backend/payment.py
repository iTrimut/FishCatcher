"""
个人收款码支付模块
适用于无商户号的个人卖家：展示收款码 + 买家截图确认
后续可升级为自动回调（需 OCR 或手动确认）
"""
import os
import json
import uuid
from datetime import datetime

from database import get_db

# 收款信息配置
PAYMENT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'payment_config.json')

DEFAULT_CONFIG = {
    "wechat_qr": "",        # 微信收款码图片路径或 base64
    "alipay_qr": "",        # 支付宝收款码图片路径或 base64
    "contact_wechat": "",   # 微信号
    "contact_qq": "",       # QQ号
    "notice": "付款后请截图发给客服，客服确认后自动发送资源链接",
    "auto_confirm": False,  # 是否开启自动确认（需配合OCR）
}


def load_config() -> dict:
    """加载支付配置"""
    if os.path.exists(PAYMENT_CONFIG_FILE):
        with open(PAYMENT_CONFIG_FILE, 'r') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG


def save_config(config: dict) -> dict:
    """保存支付配置"""
    os.makedirs(os.path.dirname(PAYMENT_CONFIG_FILE), exist_ok=True)
    with open(PAYMENT_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return {"success": True}


def create_payment_request(order_no: str, amount: float, product_name: str) -> dict:
    """生成支付请求（返回收款信息）"""
    config = load_config()
    return {
        "order_no": order_no,
        "amount": amount,
        "product_name": product_name,
        "wechat_qr": config.get("wechat_qr", ""),
        "alipay_qr": config.get("alipay_qr", ""),
        "contact_wechat": config.get("contact_wechat", ""),
        "contact_qq": config.get("contact_qq", ""),
        "notice": config.get("notice", ""),
        "payment_methods": [
            {"name": "微信支付", "available": bool(config.get("wechat_qr"))},
            {"name": "支付宝", "available": bool(config.get("alipay_qr"))},
        ],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def confirm_payment(order_no: str, confirmed_by: str = "manual") -> dict:
    """确认收款（手动或自动）"""
    conn = get_db()
    cur = conn.cursor()

    order = cur.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
    if not order:
        conn.close()
        return {"success": False, "msg": "订单不存在"}

    if order["status"] == "已完成":
        conn.close()
        return {"success": False, "msg": "订单已完成"}

    # 更新订单状态
    cur.execute("UPDATE orders SET status = '已支付' WHERE order_no = ?", (order_no,))
    conn.commit()
    conn.close()

    # 触发自动发货
    from delivery import process_delivery
    result = process_delivery(order_no)

    return {
        "success": True,
        "order_no": order_no,
        "confirmed_by": confirmed_by,
        "delivery": result,
    }


def get_pending_payments() -> list:
    """获取待确认收款的订单"""
    conn = get_db()
    rows = conn.execute(
        "SELECT o.*, p.title as product_title FROM orders o LEFT JOIN products p ON o.product_id=p.id WHERE o.status = '待支付' ORDER BY o.created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
