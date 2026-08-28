"""scraper.py 的纯逻辑测试：分类、大小提取、标签生成、去重入库。
不访问网络：只测 classify_resource / extract_size / generate_tags 与
save_resources 的去重（用临时数据库）。
"""
import sqlite3

import pytest

import scraper


# ---------- classify_resource ----------

class TestClassify:
    def test_design_material(self):
        assert scraper.classify_resource("Figma 设计资源合集") == "设计素材"

    def test_source_code(self):
        assert scraper.classify_resource("React + Next.js 项目模板", "完整源码") == "源码"

    def test_video_template(self):
        assert scraper.classify_resource("PR 转场特效包") == "视频模板"

    def test_docs_tutorial(self):
        # 注意：含源码关键词（python/react 等）的教程会优先归"源码"
        # （规则顺序：设计素材→源码→…→文档教程）。这里用纯教程词验证。
        assert scraper.classify_resource("机器学习入门教程") == "文档教程"

    def test_tool_software(self):
        assert scraper.classify_resource("Adobe 全家桶 2026 安装包") == "工具软件"

    def test_ppt_template(self):
        assert scraper.classify_resource("商业计划书 PPT 模板") == "PPT模板"

    def test_unknown_returns_default(self):
        assert scraper.classify_resource("一条没有任何关键词的消息") == "未分类"

    def test_description_also_counts(self):
        # "手写体"命中"字体"规则且不含更早规则的词（避免"设计"→设计素材 的优先级干扰）
        assert scraper.classify_resource("某资源", "免费可商用的手写体") == "字体"

    def test_keyword_priority_source_over_tutorial(self):
        # 锁定当前优先级行为：python 同时是"源码"和教程相关词，规则顺序使"源码"胜出
        assert scraper.classify_resource("Python 机器学习教程") == "源码"

    def test_keyword_priority_design_over_font(self):
        # "字体设计"含"设计"→ 命中更早的"设计素材"规则
        assert scraper.classify_resource("字体设计") == "设计素材"


# ---------- extract_size ----------

class TestExtractSize:
    def test_gb(self):
        assert scraper.extract_size("文件大小 2.3 GB") == "2.3 GB"

    def test_mb_without_space(self):
        assert scraper.extract_size("850MB 的资源") == "850 MB"

    def test_tb(self):
        assert scraper.extract_size("容量 1.5TB") == "1.5 TB"

    def test_case_insensitive(self):
        assert scraper.extract_size("约 3.2 gb") == "3.2 GB"

    def test_no_size(self):
        assert scraper.extract_size("没有任何大小信息") == ""


# ---------- generate_tags ----------

class TestGenerateTags:
    def test_has_category_and_keywords(self):
        tags = scraper.generate_tags("免费商用字体合集 2026 高清", "字体")
        assert tags[0] == "字体"
        for expected in ("免费", "可商用", "2026", "高清", "合集"):
            assert expected in tags

    def test_no_extra_keywords(self):
        assert scraper.generate_tags("普通资源", "未分类") == ["未分类"]


# ---------- save_resources 去重 ----------

def test_save_resources_deduplicates(monkeypatch, tmp_path):
    import database

    db_path = str(tmp_path / "test.db")

    def fake_get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()
    monkeypatch.setattr(scraper, "get_db", fake_get_db)

    res_a = [{
        "name": "A资源", "category": "设计素材", "description": "",
        "source_url": "", "pan_link": "", "file_size": "", "tags": '["设计素材"]',
    }]
    assert scraper.save_resources(res_a) == 1  # 首次插入
    assert scraper.save_resources(res_a) == 0  # 同名跳过（去重）

    res_b = [{
        "name": "B资源", "category": "源码", "description": "",
        "source_url": "", "pan_link": "", "file_size": "", "tags": '["源码"]',
    }]
    assert scraper.save_resources(res_b) == 1  # 不同名正常插入
