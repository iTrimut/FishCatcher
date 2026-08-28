"""pytest 公共配置：把 backend 目录加进 sys.path，并提供隔离的临时数据库 fixture。"""
import os
import sys

# 让 `import database` 可用（backend 目录在 tests/ 上一级）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import database as db


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """每个测试独立的临时数据库：不碰真实的 data/resources.db。"""
    monkeypatch.setattr(db, 'DB_PATH', str(tmp_path / 'test.db'))
    db.init_db()
    yield db
