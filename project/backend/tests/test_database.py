"""database.py 的示例测试：建表、seed 幂等、表结构、约束。"""
import sqlite3

import pytest

# fresh_db fixture 来自 conftest.py


def test_init_db_creates_all_tables(fresh_db):
    conn = fresh_db.get_db()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    expected = {"resources", "tasks", "products", "orders", "finance", "shops"}
    assert expected <= tables


def test_seed_demo_data_is_idempotent(fresh_db):
    """重复调用 seed_demo_data 不应产生重复数据（有 COUNT 早退保护）。"""
    fresh_db.seed_demo_data()
    fresh_db.seed_demo_data()  # 第二次应直接返回
    conn = fresh_db.get_db()
    count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    conn.close()
    assert count == 8


def test_seed_demo_data_counts(fresh_db):
    """seed 后各表行数符合预期。"""
    fresh_db.seed_demo_data()
    conn = fresh_db.get_db()
    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("resources", "tasks", "products", "orders", "finance", "shops")
    }
    conn.close()
    assert counts == {
        "resources": 8,
        "tasks": 5,
        "products": 5,
        "orders": 7,
        "finance": 8,
        "shops": 3,
    }


def test_products_table_has_key_columns(fresh_db):
    conn = fresh_db.get_db()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(products)")}
    conn.close()
    assert {"title", "price", "platform", "sales", "status"} <= cols


def test_orders_order_no_is_unique(fresh_db):
    """orders.order_no 有 UNIQUE 约束：重复订单号应报 IntegrityError。"""
    fresh_db.seed_demo_data()
    conn = fresh_db.get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO orders (order_no, product_id, platform) VALUES ('TB20260529001', 1, '淘宝')"
        )
    conn.close()


def test_seed_resource_fields(fresh_db):
    """seed 的第一条资源字段值正确。"""
    fresh_db.seed_demo_data()
    conn = fresh_db.get_db()
    row = conn.execute("SELECT name, category, download_count FROM resources WHERE id=1").fetchone()
    conn.close()
    assert row["name"] == "Figma 设计资源合集 2026"
    assert row["category"] == "设计素材"
    assert row["download_count"] == 1520


def test_finance_records_amounts(fresh_db):
    """财务流水包含支出（负数金额）记录。"""
    fresh_db.seed_demo_data()
    conn = fresh_db.get_db()
    expenses = conn.execute(
        "SELECT COUNT(*) FROM finance WHERE type='支出' AND amount < 0"
    ).fetchone()[0]
    conn.close()
    assert expenses == 3
