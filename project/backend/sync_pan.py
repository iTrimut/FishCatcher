"""
百度网盘 → 本地数据库 同步脚本
自动扫描网盘资源，导入到系统的 resources 表
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from baidu_pan import get_client
from database import get_db


# 自动分类规则（关键词 → 类别）
CATEGORY_RULES = {
    "影视": ["海盗", "异形", "西游", "季", "集", "电影", "剧", "高清", "CCTV", "通史", "纪录片"],
    "软件工具": ["cad", "office", "ug", "ansys", "ps", "pr", "ae", "软件", "安装"],
    "源码": ["源码", "代码", "code", "github", "项目"],
    "教程": ["教程", "入门", "精通", "详解", "视频教程", "学习"],
    "图纸素材": ["图集", "图纸", "dwg", "素材"],
    "文档资料": ["文档", "pdf", "资料", "大全"],
}


def auto_categorize(name: str) -> str:
    """根据文件夹名称自动分类"""
    name_lower = name.lower()
    for cat, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return cat
    return "其他资源"


def scan_and_sync(root_path: str = "/我的资源", depth: int = 0, max_depth: int = 2, conn=None):
    """递归扫描网盘目录并同步到数据库"""
    client = get_client()
    own_conn = False
    if conn is None:
        conn = get_db()
        own_conn = True
    cur = conn.cursor()

    print(f"\n{'  '*depth}[扫描] {root_path}")
    result = client.list_files(root_path, limit=200)

    if result.get('errno', 0) != 0:
        print(f"{'  '*depth}  ✗ 扫描失败: {result.get('errmsg', '未知错误')}")
        return []

    items = result.get('list', [])
    resources = []

    for item in items:
        name = item.get('server_filename', '')
        is_dir = item.get('isdir', 0)
        size = item.get('size', 0)
        path = item.get('path', '')

        if not name or name.startswith('.'):
            continue

        # 自动分类
        category = auto_categorize(name)

        if is_dir:
            # 文件夹 → 作为一条资源记录
            print(f"{'  '*depth}    {name} [{category}]")

            # 检查是否已存在
            existing = cur.execute("SELECT id FROM resources WHERE name = ?", (name,)).fetchone()
            if existing:
                # 更新
                cur.execute(
                    "UPDATE resources SET category=?, source_url=?, updated_at=datetime('now','localtime') WHERE id=?",
                    (category, f"baidu://{path}", existing[0])
                )
            else:
                # 新增
                cur.execute(
                    """INSERT INTO resources (name, category, description, source_url, pan_link, file_size, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'active')""",
                    (name, category, f"来自百度网盘：{path}", f"baidu://{path}", f"baidu://{path}", "文件夹",)
                )

            resources.append({"name": name, "category": category, "path": path, "is_dir": True})

            # 递归扫描子目录（仅一层）
            if depth < max_depth:
                sub_resources = scan_and_sync(path, depth + 1, max_depth, conn)
                resources.extend(sub_resources)

        else:
            # 单个文件
            size_str = ""
            if size > 1024*1024*1024:
                size_str = f"{size/(1024*1024*1024):.1f} GB"
            elif size > 1024*1024:
                size_str = f"{size/(1024*1024):.1f} MB"
            elif size > 0:
                size_str = f"{size/1024:.1f} KB"

            print(f"{'  '*depth}    {name} ({size_str})")

            existing = cur.execute("SELECT id FROM resources WHERE name = ?", (name,)).fetchone()
            if not existing:
                cur.execute(
                    """INSERT INTO resources (name, category, description, source_url, pan_link, file_size, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'active')""",
                    (name, category, f"来自百度网盘：{path}", f"baidu://{path}", f"baidu://{path}", size_str)
                )

            resources.append({"name": name, "category": category, "path": path, "size": size_str, "is_dir": False})

    conn.commit()
    if own_conn:
        conn.close()
    return resources


def run_sync():
    """执行完整同步"""
    print("=" * 50)
    print("  百度网盘资源同步")
    print("=" * 50)

    all_resources = scan_and_sync()

    # 统计
    categories = {}
    for r in all_resources:
        cat = r['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\n" + "=" * 50)
    print(f"  同步完成！共 {len(all_resources)} 个资源")
    print("  分类统计：")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")
    print("=" * 50)

    return {"total": len(all_resources), "categories": categories}


if __name__ == "__main__":
    run_sync()
