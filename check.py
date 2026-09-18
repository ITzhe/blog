# -*- coding: utf-8 -*-
"""
站点体检工具。

改了 dist/ 里的 HTML 之后跑一下，确认没弄坏东西：

    python check.py

它会检查：
  1. 结构  每篇文章是否都有该有的骨架（标题、正文、样式引用）
  2. 完整  正文是否被截断、标签是否闭合
  3. 链接  站内链接和页内锚点是否还有效
  4. 变化  和上次运行相比，哪些文章的正文被改动了

第一次运行会建立快照（把当前状态记下来），之后每次运行都会和快照对比。
快照存在 .snapshot.json，这个文件要一起提交到 git。

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
    "robots.txt",
    "sitemap.xml",
    "_headers",
    "_redirects",
    "about/index.html",
]

# 自闭合标签，不需要配对
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


def strip_tags(s):
    """得到可见文字，用于对比正文内容。"""
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "),
                 ("&#x27;", "'"), ("&middot;", "·")):
        s = s.replace(a, b)
    return os_norm(s)


def os_norm(s):
    return re.sub(r"\s+", "", s)


def body_of(path):
    """取出 <div class="article-body"> 里的内容。"""
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


def text_of(path):
    """取出页面上所有可见文字（去掉脚本、样式、导航）。"""
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"<head.*?</head>", "", raw, flags=re.S | re.I)
    return strip_tags(raw)


def check_tags(path):
    """粗略检查标签配对，找出明显没闭合的地方。"""
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
                # 有更晚开的没关，说明嵌套乱了
                return f"标签嵌套错误：</{name}> 之前的标签没有关闭"
        else:
            stack.append(name)
    if stack:
        return f"这些标签没有闭合：{', '.join(reversed(stack[-5:]))}"
    return None


def post_slugs():
    pdir = DIST / "p"
    if not pdir.is_dir():
        return []
    return sorted(d.name for d in pdir.iterdir() if d.is_dir())


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
    print("\n[1/5] 检查固定文件")
    for rel in REQUIRED_FILES:
        if (DIST / rel).exists():
            print(f"   ✓ {rel}")
        else:
            errors.append(f"缺少文件 {rel}")
            print(f"   ✗ 缺少 {rel}")

    # ---------- 2. 文章结构 ----------
    print("\n[2/5] 检查文章结构")
    slugs = post_slugs()
    if not slugs:
        errors.append("dist/p/ 下没有任何文章")
        print("   ✗ dist/p/ 下没有文章")
    bodies = {}
    for slug in slugs:
        f = DIST / "p" / slug / "index.html"
        if not f.exists():
            errors.append(f"{slug} 缺少 index.html")
            print(f"   ✗ {slug} 缺少 index.html")
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
    print(f"   共 {len(slugs)} 篇，{len(slugs) - len([e for e in errors if e.startswith(tuple(slugs))])} 篇正常")

    # ---------- 3. 链接 ----------
    print("\n[3/5] 检查链接")
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

    # ---------- 4. 和快照对比 ----------
    print("\n[4/5] 对比上次快照")
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
                n_new = len(bodies[s])
                delta = n_new - n_old
                sign = "+" if delta >= 0 else ""
                print(f"      {s}  ({sign}{delta} 字)")
        if not (added or removed or changed):
            print("   ✓ 与上次完全一致")

    save_snapshot({
        "posts": new,
        "sizes": {s: len(bodies[s]) for s in bodies},
        "total_chars": sum(len(b) for b in bodies.values()),
    })

    # ---------- 5. 总览 ----------
    print("\n[5/5] 总览")
    total_chars = sum(len(b) for b in bodies.values())
    n_files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"   文章 {len(slugs)} 篇，正文合计 {total_chars} 字")
    print(f"   站点文件 {n_files} 个")
    print(f"   首页列出 {len(re.findall(r'<li><time', (DIST / 'index.html').read_text(encoding='utf-8')))} 篇")

    # ---------- 结论 ----------
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
    if warns:
        for w in warns:
            print(f"提醒：{w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
