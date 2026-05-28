"""资源爬虫 — 抓取网站资源信息并存入数据库"""
import re
import json
import time
import hashlib
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from database import get_db

# 爬虫配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 百度网盘链接正则
PAN_PATTERN = re.compile(r'https?://pan\.baidu\.com/s/[A-Za-z0-9_-]+')
# 文件大小正则
SIZE_PATTERN = re.compile(r'(\d+\.?\d*)\s*(GB|MB|KB|TB)', re.IGNORECASE)


def classify_resource(title: str, desc: str = "") -> str:
    """根据标题和描述自动分类"""
    text = (title + " " + desc).lower()
    rules = {
        "设计素材": ["figma", "sketch", "psd", "ai", "设计", "素材", "图标", "ui kit", "组件库", "3d", "建模"],
        "源码": ["源码", "代码", "github", "react", "vue", "node", "python", "java", "typescript", "项目模板"],
        "视频模板": ["pr", "premiere", "ae", "after effects", "达芬奇", "davinci", "转场", "特效", "视频", "剪辑"],
        "文档教程": ["教程", "课程", "文档", "指南", "学习", "实战", "入门", "提示词", "prompt"],
        "工具软件": ["软件", "工具", "安装", "破解", "adobe", "notion", "docker", "安装包"],
        "字体": ["字体", "font", "字库", "手写体", "楷体", "黑体"],
        "PPT模板": ["ppt", "模板", "演示", "报告", "excel", "表格", "计划书"],
    }
    for cat, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return cat
    return "未分类"


def extract_size(text: str) -> str:
    """从文本中提取文件大小"""
    m = SIZE_PATTERN.search(text)
    if m:
        return f"{m.group(1)} {m.group(2).upper()}"
    return ""


def generate_tags(title: str, category: str) -> list:
    """自动生成标签"""
    tags = [category]
    text = title.lower()
    tag_keywords = {
        "免费": "免费", "商用": "可商用", "2026": "2026", "2025": "2025",
        "高清": "高清", "4k": "4K", "精品": "精品", "合集": "合集",
        "中文": "中文", "英文": "英文", "全套": "全套",
    }
    for kw, tag in tag_keywords.items():
        if kw in text:
            tags.append(tag)
    return tags


def scrape_page(url: str) -> list:
    """抓取单个页面的资源列表"""
    resources = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        # 尝试多种选择器找到资源条目
        items = (
            soup.select('.post-item, .article-item, .resource-item, .list-item') or
            soup.select('article') or
            soup.select('.entry, .card') or
            []
        )

        for item in items:
            # 提取标题
            title_el = item.select_one('h2, h3, .title, .entry-title, a')
            if not title_el:
                continue
            name = title_el.get_text(strip=True)
            if len(name) < 3:
                continue

            # 提取链接
            link_el = item.select_one('a')
            detail_url = link_el.get('href', '') if link_el else ''

            # 提取描述
            desc_el = item.select_one('p, .excerpt, .summary, .description')
            desc = desc_el.get_text(strip=True)[:200] if desc_el else ''

            # 提取百度网盘链接
            pan_link = ''
            pan_matches = PAN_PATTERN.findall(str(item))
            if pan_matches:
                pan_link = pan_matches[0]

            # 自动分类和标签
            category = classify_resource(name, desc)
            size = extract_size(name + " " + desc)
            tags = generate_tags(name, category)

            resources.append({
                "name": name,
                "category": category,
                "description": desc,
                "source_url": detail_url,
                "pan_link": pan_link,
                "file_size": size,
                "tags": json.dumps(tags, ensure_ascii=False),
            })

        # 如果上面的选择器都没找到，尝试从全文中提取百度网盘链接
        if not resources:
            all_pan = PAN_PATTERN.findall(resp.text)
            all_links = soup.select('a[href]')
            for link in all_links:
                href = link.get('href', '')
                title = link.get_text(strip=True)
                if len(title) > 3 and not href.startswith('#'):
                    category = classify_resource(title)
                    resources.append({
                        "name": title[:100],
                        "category": category,
                        "description": "",
                        "source_url": href,
                        "pan_link": "",
                        "file_size": "",
                        "tags": json.dumps([category], ensure_ascii=False),
                    })

    except Exception as e:
        print(f"[Scraper] 抓取失败 {url}: {e}")

    return resources


def save_resources(resources: list):
    """将爬取的资源存入数据库（去重）"""
    conn = get_db()
    cur = conn.cursor()
    new_count = 0

    for r in resources:
        # 去重：按名称检查
        existing = cur.execute("SELECT id FROM resources WHERE name = ?", (r['name'],)).fetchone()
        if existing:
            continue

        cur.execute(
            """INSERT INTO resources (name, category, description, source_url, pan_link, file_size, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (r['name'], r['category'], r['description'], r['source_url'],
             r['pan_link'], r['file_size'], r['tags'])
        )
        new_count += 1

    conn.commit()
    conn.close()
    return new_count


def run_scraper(base_url: str = "https://www.lasee.net/"):
    """执行完整爬取流程"""
    print(f"[Scraper] 开始抓取: {base_url}")
    start = time.time()

    # 抓取首页
    resources = scrape_page(base_url)
    print(f"[Scraper] 首页发现 {len(resources)} 个资源")

    # 尝试抓取分页
    for page in range(2, 6):
        for pattern in [f"{base_url}page/{page}/", f"{base_url}?page={page}"]:
            page_resources = scrape_page(pattern)
            if page_resources:
                resources.extend(page_resources)
                print(f"[Scraper] 第{page}页发现 {len(page_resources)} 个资源")
                break
            time.sleep(1)  # 礼貌延迟

    # 去重
    seen = set()
    unique = []
    for r in resources:
        key = r['name']
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # 存入数据库
    new_count = save_resources(unique)
    elapsed = time.time() - start
    print(f"[Scraper] 完成！共 {len(unique)} 个资源，新增 {new_count} 个，耗时 {elapsed:.1f}秒")
    return {"total": len(unique), "new": new_count, "elapsed": round(elapsed, 1)}


def get_resource_stats():
    """获取资源统计信息"""
    conn = get_db()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    categories = cur.execute("SELECT category, COUNT(*) as cnt FROM resources GROUP BY category ORDER BY cnt DESC").fetchall()
    conn.close()
    return {
        "total": total,
        "categories": [{"name": c[0], "count": c[1]} for c in categories],
    }


if __name__ == "__main__":
    result = run_scraper()
    print(json.dumps(result, ensure_ascii=False, indent=2))
