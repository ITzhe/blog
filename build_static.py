# -*- coding: utf-8 -*-
"""
把 Hugo 生成的 public/ 转成一套独立的纯静态 HTML 站点。

思路：
  - 只保留 20 篇文章页，URL 仍然是 /p/<slug>/，老链接和 SEO 不受影响
  - 主题、标签页、归档页、搜索页、RSS 全部丢掉
  - 样式换成一份手写的极简 CSS，不再依赖 Stack 主题
  - 文章正文直接从 Hugo 渲染好的 HTML 里抠出来，保证 <details>/<img>/代码块原样保留

输出目录：dist/
"""
import os
import re
import shutil
import html
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PUBLIC = ROOT / "public"
CONTENT = ROOT / "content" / "post"
DIST = ROOT / "dist"

SITE_NAME = "caizhe.org"
SITE_DESC = "Simple, honest, and to the point"
SITE_URL = "https://www.caizhe.org"
AUTHOR = "caizhe"
GITHUB = "https://github.com/ITzhe/blog"

# ---------------------------------------------------------------- 读取元数据

def parse_frontmatter(text):
    """解析 markdown 顶部的 YAML frontmatter，只取我们用得上的几个字段。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    body = m.group(1)
    data = {}
    for key in ("title", "date", "slug", "summary", "description"):
        km = re.search(rf'^{key}:\s*(.+?)\s*$', body, re.M)
        if km:
            v = km.group(1).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            data[key] = v
    tm = re.search(r"^tags:\s*\[(.*?)\]\s*$", body, re.M)
    data["tags"] = [t.strip().strip("\"'") for t in tm.group(1).split(",")] if tm and tm.group(1).strip() else []
    return data


def load_posts():
    posts = []
    for md in sorted(CONTENT.glob("*.md")):
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        slug = fm.get("slug") or md.stem
        src = PUBLIC / "p" / slug / "index.html"
        if not src.exists():
            print(f"  [跳过] {md.name} -> public/p/{slug}/ 不存在")
            continue
        raw = src.read_text(encoding="utf-8")
        posts.append({
            "slug": slug,
            "file": md.name,
            "title": fm.get("title", slug),
            "date": fm.get("date", ""),
            "tags": fm.get("tags", []),
            "raw": raw,
        })
    return posts


# ---------------------------------------------------------------- 抽取正文

def extract_body(raw):
    """从 Hugo 渲染好的页面里抠出 <section class=article-content>...</section>。"""
    key = "<section class=article-content>"
    i = raw.find(key)
    if i == -1:
        raise ValueError("找不到 article-content")
    start = i + len(key)
    # 从 start 开始找配对的 </section>，需要处理嵌套
    depth = 1
    pos = start
    tag_re = re.compile(r"</?section\b[^>]*>")
    while depth > 0:
        m = tag_re.search(raw, pos)
        if not m:
            raise ValueError("section 标签不配对")
        depth += -1 if m.group(0).startswith("</") else 1
        pos = m.end()
    return raw[start:pos - len("</section>")]


def clean_body(body):
    """把正文里的绝对站内链接改成相对形式，方便本地直接打开预览。"""
    body = body.replace('href=/p/', 'href=../../p/')          # 理论上文章内没有，防御性处理
    body = body.replace('href="/p/', 'href="../../p/')
    body = body.replace('src=/img/', 'src=../../img/')
    body = body.replace('src="/img/', 'src="../../img/')
    # 去掉可能残留的 disqus / 评论区
    body = re.sub(r'<div class=disqus-container>.*?</div>', "", body, flags=re.S)
    return prettify(body.strip())


# 这些标签后面直接换行，方便阅读
BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "nav", "aside",
    "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "pre", "blockquote", "table", "thead", "tbody", "tr", "details", "summary",
    "figure", "figcaption", "hr", "dl", "dt", "dd",
}
# pre / code 内部必须原样保留，绝对不能动
VERBATIM = {"pre", "code", "textarea", "script", "style"}

# 这些标签不能有闭合标签
VOID_TAGS = {
    "br", "hr", "img", "input", "meta", "link", "area",
    "base", "col", "embed", "source", "track", "wbr",
}


def prettify(src):
    """
    把 Hugo 压成一整行的正文拆成带缩进的多行，方便直接用编辑器改。
    渲染效果完全不变，只是可读性变好。pre / code 内部原样保留。
    """
    out = []
    indent = 0
    i = 0
    n = len(src)

    def push(line):
        out.append("  " * max(indent, 0) + line)

    while i < n:
        lt = src.find("<", i)

        # 没有更多标签，剩下的都是文字
        if lt == -1:
            text = src[i:].strip()
            if text:
                push(text)
            break

        # 标签之前的文字
        text = src[i:lt].strip()
        if text:
            push(text)

        gt = src.find(">", lt)
        if gt == -1:
            rest = src[lt:].strip()
            if rest:
                push(rest)
            break

        tag = src[lt:gt + 1]
        i = gt + 1

        m = re.match(r"</?\s*([a-zA-Z0-9]+)", tag)
        name = m.group(1).lower() if m else ""
        closing = tag.startswith("</")
        void = name in VOID_TAGS or tag.endswith("/>")

        # 注释：整块当一行
        if tag.startswith("<!--"):
            push(tag)
            continue

        # pre / code / script / style：原样吞掉，绝不格式化
        if name in VERBATIM:
            if closing:
                indent = max(indent - 1, 0)
                push(tag)
                continue
            end_tag = f"</{name}>"
            end = src.find(end_tag, i)
            if end == -1:
                push(tag + src[i:])
                break
            push(tag + src[i:end] + end_tag)
            i = end + len(end_tag)
            continue

        if closing:
            indent = max(indent - 1, 0)
            push(tag)
        elif void:
            push(tag)
        elif name in BLOCK_TAGS:
            push(tag)
            indent += 1
        else:
            # 行内标签（a / strong / em / span …）和它的内容绑成一行
            end_tag = f"</{name}>"
            end = src.find(end_tag, i) if name else -1
            if end != -1 and "<" not in src[i:end]:
                push(src[lt:end + len(end_tag)])
                i = end + len(end_tag)
            else:
                push(tag)

    # 去掉连续空行
    clean = []
    for ln in out:
        if not ln.strip() and (not clean or not clean[-1].strip()):
            continue
        clean.append(ln.rstrip())
    return "\n".join(clean)


def extract_toc(raw):
    """抽出目录，没有就返回空串。"""
    m = re.search(r"<nav id=TableOfContents>(.*?)</nav>", raw, re.S)
    return m.group(1) if m else ""


def extract_reading_time(raw):
    m = re.search(r"article-time--reading>([^<]+)<", raw)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- 日期格式化

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not m:
        return iso
    y, mo, d = m.groups()
    return f"{MONTHS[int(mo) - 1]} {int(d):02d}, {y}"


# ---------------------------------------------------------------- HTML 模板

CSS = """/* 极简样式 —— 手写，无依赖 */
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #6b7280;
  --border: #e5e7eb;
  --code-bg: #f6f8fa;
  --link: #0969da;
  --max: 46rem;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181d;
    --fg: #e6e6e6;
    --muted: #9099a8;
    --border: #2b2f36;
    --code-bg: #1e2128;
    --link: #6cb6ff;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font: 16px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
}
.wrap { max-width: var(--max); margin: 0 auto; padding: 0 1.25rem; }

/* 页头 */
.site-header {
  border-bottom: 1px solid var(--border);
  padding: 1.5rem 0;
  margin-bottom: 2.5rem;
}
.site-header .wrap { display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
.site-title { font-size: 1.1rem; font-weight: 600; margin: 0; }
.site-title a { color: var(--fg); text-decoration: none; }
.site-nav { margin-left: auto; display: flex; gap: 1.1rem; font-size: .9rem; }
.site-nav a { color: var(--muted); text-decoration: none; }
.site-nav a:hover { color: var(--link); }

/* 文章列表 */
.post-list { list-style: none; padding: 0; margin: 0; }
.post-list li {
  display: flex; align-items: baseline; gap: 1rem;
  padding: .7rem 0; border-bottom: 1px solid var(--border);
}
.post-list li:last-child { border-bottom: none; }
.post-list time {
  color: var(--muted); font-size: .82rem; white-space: nowrap;
  font-variant-numeric: tabular-nums; min-width: 6.5rem;
}
.post-list a { color: var(--fg); text-decoration: none; flex: 1; }
.post-list a:hover { color: var(--link); }

/* 文章页 */
article { padding-bottom: 3rem; }
.article-header { margin-bottom: 2rem; }
.article-title { font-size: 1.7rem; line-height: 1.3; margin: 0 0 .6rem; }
.article-meta { color: var(--muted); font-size: .85rem; display: flex; gap: .9rem; flex-wrap: wrap; }

.article-body h2 {
  font-size: 1.3rem; margin: 2.2rem 0 .8rem;
  padding-bottom: .3rem; border-bottom: 1px solid var(--border);
}
.article-body h3 { font-size: 1.1rem; margin: 1.8rem 0 .6rem; }
.article-body p { margin: 1rem 0; }
.article-body a { color: var(--link); }
.article-body ul, .article-body ol { padding-left: 1.5rem; }
.article-body li { margin: .35rem 0; }
.article-body blockquote {
  margin: 1.2rem 0; padding: .3rem 1rem;
  border-left: 3px solid var(--border); color: var(--muted);
}
.article-body img { max-width: 100%; height: auto; }
.article-body hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
.article-body table {
  border-collapse: collapse; width: 100%; margin: 1.2rem 0;
  font-size: .92rem; display: block; overflow-x: auto;
}
.article-body th, .article-body td {
  border: 1px solid var(--border); padding: .5rem .7rem; text-align: left;
}
.article-body th { background: var(--code-bg); }

.article-body pre {
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 6px; padding: .9rem 1rem; overflow-x: auto;
  font-size: .86rem; line-height: 1.6;
}
.article-body code {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
               "Liberation Mono", monospace;
}
.article-body :not(pre) > code {
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 4px; padding: .12em .38em; font-size: .88em;
}
.article-body details {
  border: 1px solid var(--border); border-radius: 6px;
  padding: .6rem 1rem; margin: 1.2rem 0;
}
.article-body summary { cursor: pointer; font-weight: 600; }

/* 标签 */
.tags { margin-top: 2.5rem; padding-top: 1.2rem; border-top: 1px solid var(--border); font-size: .85rem; }
.tags a {
  display: inline-block; margin: 0 .4rem .4rem 0; padding: .15rem .6rem;
  border: 1px solid var(--border); border-radius: 999px;
  color: var(--muted); text-decoration: none;
}
.tags a:hover { color: var(--link); border-color: var(--link); }

/* 目录 */
.toc {
  border: 1px solid var(--border); border-radius: 6px;
  padding: .8rem 1rem; margin: 0 0 2rem; font-size: .9rem;
}
.toc-title { font-weight: 600; margin-bottom: .4rem; font-size: .85rem; color: var(--muted); }
.toc ul { margin: 0; padding-left: 1.2rem; }
.toc li { margin: .2rem 0; }
.toc a { color: var(--muted); text-decoration: none; }
.toc a:hover { color: var(--link); }

/* 页脚 */
.site-footer {
  border-top: 1px solid var(--border); margin-top: 3rem;
  padding: 1.5rem 0 3rem; color: var(--muted); font-size: .82rem;
}
.site-footer a { color: var(--muted); }

/* 归档 */
.archive-year { font-size: 1.15rem; font-weight: 600; margin: 2rem 0 .6rem; }

@media (max-width: 600px) {
  .post-list li { flex-direction: column; gap: .15rem; }
  .article-title { font-size: 1.4rem; }
}
"""


def page_shell(title, desc, rel_root, body, canon_path="/", extra_head=""):
    """
    所有页面共用的外壳。
    rel_root  相对站点根的前缀（首页 ''、文章页 '../../'）
    canon_path 该页在站点里的绝对路径（用于 canonical），以 / 开头以 / 结尾
    """
    full_title = f"{title} · {SITE_NAME}" if title else f"{SITE_NAME} — {SITE_DESC}"
    home = rel_root or "./"          # 首页 rel_root 为空串，用 "./" 避免 href=""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{SITE_URL}{canon_path}">
<link rel="stylesheet" href="{rel_root}style.css">
<link rel="icon" href="{rel_root}favicon.ico">
{extra_head}</head>
<body>
<header class="site-header">
  <div class="wrap">
    <h1 class="site-title"><a href="{home}">{SITE_NAME}</a></h1>
    <nav class="site-nav">
      <a href="{home}">Home</a>
      <a href="{rel_root}about/">About</a>
      <a href="{GITHUB}">GitHub</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    &copy; {AUTHOR} &middot; <a href="{rel_root}about/">About</a>
  </div>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- 开始构建

def clean_out():
    """
    清空 dist/。故意不整目录删除 —— 删除整个目录在文件被占用时
    （比如本地预览服务器还在跑）会直接失败。改成逐个删文件，
    已被占用的文件跳过并提示，不影响其余部分。
    """
    if not DIST.exists():
        DIST.mkdir(parents=True)
        return
    locked = []
    for item in sorted(DIST.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if item.is_dir():
                item.rmdir()
            else:
                item.unlink()
        except OSError:
            locked.append(item)
    if locked:
        print(f"  提示：{len(locked)} 个文件被占用，未能清除（本地预览服务器可先关掉）")
        for x in locked[:5]:
            print(f"    {x.relative_to(ROOT)}")


def main():
    clean_out()

    posts = load_posts()
    print(f"读到 {len(posts)} 篇")

    # 1) 抽出正文
    for p in posts:
        p["body"] = clean_body(extract_body(p["raw"]))
        p["toc"] = extract_toc(p["raw"])
        p["rt"] = extract_reading_time(p["raw"])
    posts.sort(key=lambda x: x["date"], reverse=True)

    # 2) style.css
    (DIST / "style.css").write_text(CSS, encoding="utf-8")

    # 3) 图标（复用原来那张）
    src_ico = ROOT / "static" / "favicon.ico"
    if not src_ico.exists():
        src_ico = ROOT / "public" / "logo.ico"
    if src_ico.exists():
        shutil.copy2(src_ico, DIST / "favicon.ico")
        print("favicon 已复制")

    # 4) 首页（按日期倒序的文章列表）
    items = []
    for p in posts:
        items.append(
            f'      <li><time datetime="{p["date"][:10]}">{fmt_date(p["date"])}</time>'
            f'<a href="p/{p["slug"]}/">{html.escape(p["title"])}</a></li>'
        )
    home_body = (
        f'<h2 class="archive-year">All posts ({len(posts)})</h2>\n'
        f'    <ul class="post-list">\n' + "\n".join(items) + "\n    </ul>"
    )
    (DIST / "index.html").write_text(
        page_shell("", SITE_DESC, "", home_body, canon_path="/"), encoding="utf-8")

    # 5) 文章页
    for p in posts:
        toc_html = ""
        if p["toc"]:
            toc_html = (f'<nav class="toc">\n'
                        f'      <div class="toc-title">Table of contents</div>\n'
                        f'      {p["toc"]}\n    </nav>\n    ')
        tags_html = ""
        if p["tags"]:
            links = "".join(
                f'<a href="../../tags/{t.lower().replace(" ", "-")}/">{html.escape(t)}</a>'
                for t in p["tags"]
            )
            tags_html = f'\n    <div class="tags">{links}</div>'
        # 文章内的目录锚点：把绝对路径的站内链接修掉
        body = p["body"]
        desc = re.sub(r"<[^>]+>", " ", body)[:160].strip()

        art = f"""<article>
    <header class="article-header">
      <h1 class="article-title">{html.escape(p["title"])}</h1>
      <div class="article-meta">
        <time datetime="{p["date"][:10]}">{fmt_date(p["date"])}</time>
        <span>{p["rt"]}</span>
      </div>
    </header>
    {toc_html}<div class="article-body">
    {body}
    </div>{tags_html}
    </article>"""
        out = DIST / "p" / p["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            page_shell(p["title"], desc, "../../", art,
                       canon_path=f"/p/{p['slug']}/"), encoding="utf-8")

    print(f"首页 + {len(posts)} 篇文章页 已生成")

    # 6) 关于页
    about_src = PUBLIC / "about" / "index.html"
    if about_src.exists():
        raw = about_src.read_text(encoding="utf-8")
        ab = clean_body(extract_body(raw))
        ab_body = f"""<article>
    <header class="article-header">
      <h1 class="article-title">About</h1>
      <div class="article-meta">
        <span>Notes on Linux, Kubernetes, and cloud-native infrastructure</span>
      </div>
    </header>
    <div class="article-body">
    {ab}
    </div>
    </article>"""
        out = DIST / "about"
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            page_shell("About",
                       "Notes on Linux, Kubernetes, and cloud-native infrastructure",
                       "../", ab_body, canon_path="/about/"), encoding="utf-8")
        print("关于页 已生成")

    # 7) 标签页：按"只留文章"的思路，不做独立标签页，
    #    但文章页底部的标签仍然给出 —— 统一指回首页并按标签分组。
    #    这里生成 tags/<tag>/ 页面，列出该标签下的文章，避免断链。
    tagmap = {}
    for p in posts:
        for t in p["tags"]:
            tagmap.setdefault(t, []).append(p)
    for tag, group in tagmap.items():
        tslug = tag.lower().replace(" ", "-")
        rows = "\n".join(
            f'      <li><time datetime="{x["date"][:10]}">{fmt_date(x["date"])}</time>'
            f'<a href="../../p/{x["slug"]}/">{html.escape(x["title"])}</a></li>'
            for x in sorted(group, key=lambda y: y["date"], reverse=True)
        )
        tb = (f'<h2 class="archive-year">{html.escape(tag)} '
              f'({len(group)})</h2>\n    <ul class="post-list">\n{rows}\n    </ul>')
        out = DIST / "tags" / tslug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            page_shell(tag, f"Posts tagged {tag}", "../../", tb,
                       canon_path=f"/tags/{tslug}/"), encoding="utf-8")
    print(f"标签页 已生成 {len(tagmap)} 个")

    # 8) 404 页
    #    404.html 本身放在站点根目录，页内链接用相对路径即可，
    #    本地预览和线上部署都能正确解析。
    nf = ('<h2 class="archive-year">Page not found</h2>\n'
          '    <p>That page is not here. Try the '
          '<a href="./">home page</a>.</p>')
    (DIST / "404.html").write_text(
        page_shell("Page not found", "Page not found", "", nf,
                   canon_path="/404.html"), encoding="utf-8")

    # 9) Cloudflare 安全响应头
    (DIST / "_headers").write_text("""# Cloudflare Pages 响应头配置
# 官方文档：https://developers.cloudflare.com/pages/configuration/headers/

/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=()

# 静态资源长缓存
/style.css
  Cache-Control: public, max-age=604800

/favicon.ico
  Cache-Control: public, max-age=604800
""", encoding="utf-8")

    # 10) Cloudflare 跳转规则
    redirects = build_redirects()
    (DIST / "_redirects").write_text(redirects, encoding="utf-8")

    # 11) robots.txt
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8")

    # 12) sitemap.xml
    urls = [f"{SITE_URL}/", f"{SITE_URL}/about/"]
    urls += [f"{SITE_URL}/p/{p['slug']}/" for p in posts]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc></url>")
    sm.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")

    print("404 / _headers / _redirects / robots / sitemap 已生成")
    return posts


def build_redirects():
    """旧中文 URL -> 新英文 URL 的 301 规则。"""
    pairs = [
        ("301%E5%92%8C302%E5%8C%BA%E5%88%AB", "301-vs-302-redirect"),
        ("bind-dlz", "bind-dlz"),
        ("clamv", "clamav"),
        ("containerd%E5%AE%89%E8%A3%85", "containerd-install"),
        ("containerd%E5%B8%B8%E7%94%A8%E5%91%BD%E4%BB%A4", "containerd-commands"),
        ("docker%E5%AE%89%E8%A3%85es", "docker-elasticsearch"),
        ("docker%E5%AE%89%E8%A3%85keepalived", "docker-keepalived"),
        ("docker%E5%AE%89%E8%A3%85openldap", "docker-openldap"),
        ("docker%E5%AE%89%E8%A3%85redis-cluster", "docker-redis-cluster"),
        ("gitlab%E5%A4%A7%E6%96%87%E4%BB%B6%E6%B8%85%E7%90%86", "gitlab-purge-large-files"),
        ("glusterfs%E5%88%86%E5%B8%83%E5%BC%8F%E5%AD%98%E5%82%A8", "glusterfs-distributed-storage"),
        ("kubenertes1.22%E9%AB%98%E5%8F%AF%E7%94%A8%E5%AE%89%E8%A3%85", "kubernetes-1-22-ha-install"),
        ("kubernetesapi%E8%B0%83%E7%94%A8%E6%96%B9%E6%B3%95", "kubernetes-api-calls"),
        ("kvm%E8%99%9A%E6%8B%9F%E6%9C%BA", "kvm-virtual-machines"),
        ("letsencrypt", "letsencrypt-acme-sh"),
        ("linux%E7%B3%BB%E7%BB%9F%E4%BC%98%E5%8C%96", "linux-system-tuning"),
        ("nginx-%E5%8A%A0%E6%96%9C%E7%BA%BF%E7%9A%84%E5%8C%BA%E5%88%AB", "nginx-trailing-slash"),
        ("nginx%E4%BC%98%E5%8C%96", "nginx-tuning"),
        ("redis%E4%BC%98%E5%8C%96", "redis-tuning"),
    ]
    lines = [
        "# Cloudflare Pages 跳转规则",
        "# 官方文档：https://developers.cloudflare.com/pages/configuration/redirects/",
        "#",
        "# 本站由 Hugo 迁为纯静态 HTML，URL 结构保持不变，旧链接继续有效。",
        "# 旧 slug 含中文，已做百分号编码。",
        "# 规则按先后顺序匹配，第一条命中的生效，顺序不要随意调整。",
        "",
        "# --- 文章：旧中文 slug -> 新 slug ---",
        "",
    ]
    for old, new in pairs:
        if old == new:
            continue
        lines.append(f"/p/{old}/    /p/{new}/    301")
    lines += [
        "",
        "# --- 页面 ---",
        "",
        "/%E5%85%B3%E4%BA%8E/                /about/    301",
        "/%E5%8F%8B%E6%83%85%E9%93%BE%E6%8E%A5/  /            301",
        "/about-us/                          /about/    301",
        "/about-hugo/                        /about/    301",
        "/contact/                           /about/    301",
        "/links/                             /            301",
        "",
        "# --- Hugo 时代自动生成的页面，现已取消 ---",
        "",
        "/archives/    /    301",
        "/search/      /    301",
        "/page/*       /    301",
        "/post/*       /    301",
        "/categories/* /    301",
        "/ts/*         /    301",
        "",
        "# --- 语言前缀：本站为根路径下的纯英文站点 ---",
        "",
        "/en/*      /:splat    301",
        "/zh-cn/*   /:splat    301",
        "/ar/*      /:splat    301",
        "",
        "# --- 裸域统一跳到 www（DNS 层面建议配置同样规则） ---",
        "",
        "https://caizhe.org/*    https://www.caizhe.org/:splat    301",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
