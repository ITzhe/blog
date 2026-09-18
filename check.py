# -*- coding: utf-8 -*-
"""
站点体检工具。

改了 dist/ 里的 HTML 之后跑一下，确认没弄坏东西：

    python check.py

这是一个纯静态 HTML 网站：只有文章、首页、关于页。
没有构建步骤，没有框架，没有 SEO 文件。

检查内容：
  1. 结构  每个页面是否都有该有的骨架
  2. 完整  正文是否被截断、标签是否闭合
  3. 链接  站内链接和页内锚点是否还有效
  4. 变化  和上次运行相比，哪些文章的正文被改动了

第一次运行会建立快照（.snapshot.json），之后每次运行都与之对比。
快照文件要一起提交到 git。

退出码 0 = 一切正常，1 = 发现问题。
"""
import re
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DIST = ROOT / "dist"
SNAPSHOT = ROOT / ".snapshot.json"

# 站点里应该有的固定文件
REQUIRED_FILES = [
    "index.html",
    "404.html",
    "style.css",
    "favicon.ico",
    "about/index.html",
    "search-index.json",
]

# 不希望再出现的文件（已废弃的 SEO / 老站遗留）
FORBIDDEN_FILES = [
    "sitemap.xml",
    "robots.txt",
    "_redirects",
    "_headers",
    "feed.xml",
]

# 不希望再出现在 HTML 里的东西
FORBIDDEN_PATTERNS = [
    (r'<link rel="canonical"', "canonical 链接"),
    (r'<meta property="og:', "og 标签"),
    (r'<meta name="twitter:', "twitter 标签"),
    (r'<meta name="description"', "description meta"),
    (r'href="[^"]*tags/', "指向已删除标签页的链接"),
]

# 单独跟踪的待办项（不算错误，只提示）
TODO_PATTERNS = [
    (r'https://caizhe-img\.oss-cn-beijing\.aliyuncs\.com',
     "阿里云 OSS 图片（计划迁往 Cloudflare R2）"),
]

# 分类页目录（由 gen_categories.py 生成，不是文章，不参与正文检查）
CATEGORY_DIRS = ["docker", "kubernetes", "networking",
                 "storage", "systems", "troubleshooting", "other"]

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "),
                 ("&#x27;", "'"), ("&middot;", "·")):
        s = s.replace(a, b)
    return re.sub(r"\s+", "", s)


def body_of(path):
    raw = path.read_text(encoding="utf-8")
    key = '<div class="article-body">'
    i = raw.find(key)
    if i == -1:
        return None
    start = i + len(key)
    depth = 1
    pos = start
    tag_re = re.compile(r"</?div\b[^>]*>")
    while depth > 0:
        m = tag_re.search(raw, pos)
        if not m:
            return None
        depth += -1 if m.group(0).startswith("</") else 1
        pos = m.end()
    return raw[start:pos - len("</div>")]


def check_tags(path):
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S | re.I)
    stack = []
    for m in re.finditer(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>", raw):
        closing, name, selfclose = m.group(1), m.group(2).lower(), m.group(3)
        if name in VOID_TAGS or selfclose or name == "!doctype":
            continue
        if closing:
            if stack and stack[-1] == name:
                stack.pop()
            elif name in stack:
                return f"标签嵌套错误：</{name}> 之前的标签没有关闭"
        else:
            stack.append(name)
    if stack:
        return f"这些标签没有闭合：{', '.join(reversed(stack[-5:]))}"
    return None


def post_dirs():
    """文章目录：dist/ 下除了 about 和分类页之外的一级目录。"""
    return sorted(d.name for d in DIST.iterdir()
                  if d.is_dir() and d.name != "about"
                  and d.name not in CATEGORY_DIRS)


def load_snapshot():
    if SNAPSHOT.exists():
        try:
            return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_snapshot(data):
    SNAPSHOT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")


def main():
    errors = []
    warns = []

    print("=" * 66)
    print("站点体检")
    print("=" * 66)

    # ---------- 1. 固定文件 ----------
    print("\n[1/6] 检查固定文件")
    for rel in REQUIRED_FILES:
        if (DIST / rel).exists():
            print(f"   ✓ {rel}")
        else:
            errors.append(f"缺少文件 {rel}")
            print(f"   ✗ 缺少 {rel}")

    print("\n[2/6] 检查是否残留老站文件")
    found = False
    for name in FORBIDDEN_FILES:
        if (DIST / name).exists():
            errors.append(f"不该存在的文件：{name}")
            print(f"   ✗ 不该存在：{name}")
            found = True
    if (DIST / "tags").is_dir():
        errors.append("不该存在的目录：tags/")
        print("   ✗ 不该存在：tags/")
        found = True
    if not found:
        print("   ✓ 没有残留")

    # ---------- 3. 文章结构 ----------
    print("\n[3/6] 检查文章结构")
    slugs = post_dirs()
    if not slugs:
        errors.append("dist/ 下没有任何文章目录")
        print("   ✗ dist/ 下没有文章")
    bodies = {}
    bad_count = 0
    for slug in slugs:
        f = DIST / slug / "index.html"
        if not f.exists():
            errors.append(f"{slug} 缺少 index.html")
            print(f"   ✗ {slug} 缺少 index.html")
            bad_count += 1
            continue
        raw = f.read_text(encoding="utf-8")
        problems = []
        if "<title>" not in raw:
            problems.append("没有标题")
        if 'class="article-body"' not in raw:
            problems.append("没有正文区")
        if "style.css" not in raw:
            problems.append("没有引用样式")
        if not re.search(r'<h1 class="article-title">', raw):
            problems.append("没有文章标题")
        tag_err = check_tags(f)
        if tag_err:
            problems.append(tag_err)
        b = body_of(f)
        if b is None:
            problems.append("正文区标签没闭合")
        else:
            bodies[slug] = strip_tags(b)
            if len(bodies[slug]) < 30:
                problems.append(f"正文太短（{len(bodies[slug])} 字）")
        if problems:
            errors.append(f"{slug}: {'; '.join(problems)}")
            print(f"   ✗ {slug}: {'; '.join(problems)}")
            bad_count += 1
    print(f"   共 {len(slugs)} 篇，{len(slugs) - bad_count} 篇正常")

    # ---------- 3b. 分类页 ----------
    print("\n[3b/6] 检查分类页")
    cat_bad = 0
    cat_post_slugs = set()
    for cat in CATEGORY_DIRS:
        f = DIST / cat / "index.html"
        if not f.exists():
            errors.append(f"缺失分类页 {cat}/index.html")
            print(f"   ✗ 缺失 {cat}/index.html")
            cat_bad += 1
            continue
        raw = f.read_text(encoding="utf-8")
        problems = []
        if "<title>" not in raw:
            problems.append("没有标题")
        if 'class="page-title"' not in raw:
            problems.append("没有分类标题")
        if "post-list" not in raw:
            problems.append("没有文章列表")
        # 分类页里的文章链接，收集起来做交叉验证
        for m in re.finditer(r'href="\.\./([a-z0-9-]+)/"', raw):
            cat_post_slugs.add(m.group(1))
        tag_err = check_tags(f)
        if tag_err:
            problems.append(tag_err)
        if problems:
            errors.append(f"{cat}/: {'; '.join(problems)}")
            print(f"   ✗ {cat}/: {'; '.join(problems)}")
            cat_bad += 1
    print(f"   共 {len(CATEGORY_DIRS)} 个，{len(CATEGORY_DIRS) - cat_bad} 个正常")

    # 交叉验证：分类页引用的文章必须真实存在，且每篇文章都被某个分类收录
    for s in sorted(cat_post_slugs):
        if not (DIST / s / "index.html").exists():
            errors.append(f"分类页引用了不存在的文章：{s}")
            print(f"   ✗ 分类页引用了不存在的文章：{s}")
    for s in slugs:
        if s not in cat_post_slugs:
            errors.append(f"文章没有被任何分类收录：{s}")
            print(f"   ✗ 文章没有被任何分类收录：{s}")

    # ---------- 3c. 搜索索引 ----------
    print("\n[3c/6] 检查搜索索引")
    idx_file = DIST / "search-index.json"
    if not idx_file.exists():
        errors.append("缺少 search-index.json")
        print("   ✗ 缺少 search-index.json")
    else:
        try:
            idx = json.loads(idx_file.read_text(encoding="utf-8"))
            idx_slugs = {e["u"].rstrip("/") for e in idx}
            # 索引里的每篇文章必须存在
            for s in sorted(idx_slugs):
                if not (DIST / s / "index.html").exists():
                    errors.append(f"搜索索引指向不存在的文章：{s}")
                    print(f"   ✗ 搜索索引指向不存在的文章：{s}")
            # 每篇文章都必须能被搜到
            for s in slugs:
                if s not in idx_slugs:
                    errors.append(f"文章不在搜索索引里：{s}")
                    print(f"   ✗ 文章不在搜索索引里：{s}")
            print(f"   ✓ {len(idx)} 条，与 {len(slugs)} 篇文章一一对应")
        except Exception as e:
            errors.append(f"search-index.json 解析失败：{e}")
            print(f"   ✗ 解析失败：{e}")

    # 首页不该再直接罗列文章（文章入口在分类页）
    # 注意：搜索结果里也有 post-list，但那是 <script> 动态生成的字面量，
    # 所以先把 <script> 整段剥掉再判断。
    idx_html = (DIST / "index.html").read_text(encoding="utf-8")
    idx_static = re.sub(r"<script.*?</script>", "", idx_html, flags=re.S | re.I)
    if 'id="q"' not in idx_html:
        errors.append("首页缺少搜索框")
        print("   ✗ 首页缺少搜索框")
    if 'class="post-list"' in idx_static:
        errors.append("首页不该再直接列出文章，入口应在分类页")
        print("   ✗ 首页仍在直接列出文章")
    if "cat-card" not in idx_html:
        errors.append("首页缺少分类卡片")
        print("   ✗ 首页缺少分类卡片")

    # ---------- 4. 链接 ----------
    print("\n[4/6] 检查链接")
    dead, anchors_bad, anchor_total = [], [], 0
    for f in DIST.rglob("*.html"):
        txt = f.read_text(encoding="utf-8")
        ids = set(re.findall(r'id=["\']?([a-zA-Z0-9_-]+)', txt))
        rel = f.relative_to(DIST)
        for m in re.finditer(r'(?:href|src)=["\']?([^"\'\s>]*)', txt):
            u = m.group(1)
            if not u or u.startswith(("http://", "https://", "//", "mailto:", "data:")):
                continue
            if u.startswith("#"):
                anchor_total += 1
                if u[1:] and u[1:] not in ids:
                    anchors_bad.append(f"{rel} → {u}")
                continue
            target = (f.parent / u.split("#")[0]).resolve()
            if u.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                dead.append(f"{rel} → {u}")
    if dead:
        errors.extend(dead)
        print(f"   ✗ 断链 {len(dead)} 个：")
        for d in dead[:10]:
            print(f"      {d}")
    else:
        print("   ✓ 没有断链")
    if anchors_bad:
        errors.extend(anchors_bad)
        print(f"   ✗ 失效锚点 {len(anchors_bad)} 个：")
        for a in anchors_bad[:10]:
            print(f"      {a}")
    else:
        print(f"   ✓ {anchor_total} 个页内锚点全部有效")

    # ---------- 5. 不该出现的东西 ----------
    print("\n[5/6] 检查不该出现的内容")
    hits = {desc: [] for _, desc in FORBIDDEN_PATTERNS}
    for f in DIST.rglob("*.html"):
        txt = f.read_text(encoding="utf-8")
        rel = f.relative_to(DIST)
        for pat, desc in FORBIDDEN_PATTERNS:
            if re.search(pat, txt):
                hits[desc].append(str(rel))
    found2 = False
    for desc, files in hits.items():
        if files:
            found2 = True
            errors.append(f"发现 {desc}：{', '.join(files[:3])}")
            print(f"   ✗ {desc}（{len(files)} 个文件）")
    if not found2:
        print("   ✓ 干净")

    # 待办项：不算错误
    print("\n[待办]")
    todo_found = False
    for pat, desc in TODO_PATTERNS:
        files = []
        for f in DIST.rglob("*.html"):
            if re.search(pat, f.read_text(encoding="utf-8")):
                files.append(str(f.relative_to(DIST)))
        if files:
            todo_found = True
            print(f"   · {desc}：{len(files)} 个文件")
            for x in files[:3]:
                print(f"       {x}")
    if not todo_found:
        print("   ✓ 无待办")

    # ---------- 6. 和快照对比 ----------
    print("\n[6/6] 对比上次快照")
    old = load_snapshot()
    new = {slug: hashlib.sha256(bodies[slug].encode()).hexdigest()[:16]
           for slug in sorted(bodies)}
    if not old:
        print("   （第一次运行，建立快照）")
    else:
        old_posts = old.get("posts", {})
        added = [s for s in new if s not in old_posts]
        removed = [s for s in old_posts if s not in new]
        changed = [s for s in new if s in old_posts and new[s] != old_posts[s]]
        if added:
            print(f"   新增 {len(added)} 篇：{', '.join(added)}")
        if removed:
            warns.append(f"文章减少：{', '.join(removed)}")
            print(f"   ⚠ 少了 {len(removed)} 篇：{', '.join(removed)}")
        if changed:
            print(f"   ℹ 正文有改动 {len(changed)} 篇：")
            for s in changed:
                n_old = old.get("sizes", {}).get(s, 0)
                delta = len(bodies[s]) - n_old
                sign = "+" if delta >= 0 else ""
                print(f"      {s}  ({sign}{delta} 字)")
        if not (added or removed or changed):
            print("   ✓ 与上次完全一致")

    save_snapshot({
        "posts": new,
        "sizes": {s: len(bodies[s]) for s in bodies},
        "total_chars": sum(len(b) for b in bodies.values()),
    })

    # ---------- 总览 ----------
    print("\n[总览]")
    total_chars = sum(len(b) for b in bodies.values())
    n_files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"   文章 {len(slugs)} 篇，正文合计 {total_chars} 字")
    print(f"   站点文件 {n_files} 个")

    print("\n" + "=" * 66)
    if errors:
        print(f"发现 {len(errors)} 个问题，需要修复：")
        for e in errors[:20]:
            print(f"  · {e}")
        if len(errors) > 20:
            print(f"  …… 还有 {len(errors) - 20} 个")
        print("\n提示：可以用 git 撤销改动")
        print("   git checkout -- dist/")
        return 1
    print("一切正常 ✓")
    for w in warns:
        print(f"提醒：{w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
