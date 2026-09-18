# -*- coding: utf-8 -*-
"""
给 dist/ 下所有页面注入 SEO 标签，并生成 sitemap.xml / robots.txt / feed.xml。

设计：
  - 幂等。靠 <!-- seo:start --> ... <!-- seo:end --> 标记块，
    重复运行只替换标记块内的内容，不会重复叠加。
  - 不改正文。只动 <head> 里的标记块，article-body 一个字节都不碰。
  - canonical 一律指向 https://www.caizhe.org/，因为裸域已经 301 到 www，
    pages.dev 是 Cloudflare 自动给的域名、跳不掉，只能靠 canonical 收敛。

被 gen_categories.py 在最后调用，也可以单独运行：
    python gen_seo.py
"""
import io
import os
import re
import html as _html
import datetime
import json

DIST = "dist"
SITE = "https://www.caizhe.org"
SITE_NAME = "caizhe.org"
AUTHOR = "caizhe"

# 首页/关于页/404 的固定文案（其余页面自动从正文提取）
STATIC_DESC = {
    "": "Notes on Linux, Kubernetes, and cloud-native infrastructure — "
        "runbooks, configs, and the reasoning behind them.",
    "about/": "Notes on Linux, Kubernetes, and cloud-native infrastructure. "
              "Runbooks written to be useful to my future self first.",
    "404.html": "That page is not here. Browse the archive by topic instead — "
                "Docker, Kubernetes, networking, storage, systems.",
}

# 自动摘要有几篇效果不好（正文几乎全是配置块，或开头是零散标签行）。
# 这些手写覆盖，写在 <slug>/ 里。
POST_DESC = {
    "docker-keepalived/":
        "Running Keepalived under Docker for a floating VIP: the master and "
        "backup node configs, health checks, and how the failover behaves.",
    "containerd-commands/":
        "A practical ctr cheat sheet — pull, list, tag, remove, mount, export, "
        "and import images, plus the content digest not found error.",
    "bind-dlz/":
        "Building BIND with DLZ and a MySQL backend: dependencies, the schema, "
        "named.conf, and removing the anonymous users that break the build.",
    "nginx-trailing-slash/":
        "Why a trailing slash changes Nginx behaviour — the difference between "
        "location and proxy_pass rules, with test URLs and both cases.",
    "linux-system-tuning/":
        "Production Linux tuning: trimming startup services, hardening SSH, and "
        "the kernel parameters for ports, TIME_WAIT, and connection tracking.",
    "kubernetes-1-22-ha-install/":
        "A high-availability Kubernetes 1.22 cluster from bare Ubuntu: kernel "
        "prerequisites, containerd, kubeadm, the Aliyun mirror, and ingress.",
    "glusterfs-distributed-storage/":
        "GlusterFS distributed versus replicated volumes, how brick hashing "
        "places files, and the trade-offs between the two volume types.",
    "kubernetes-api-calls/":
        "Three ways to call the Kubernetes API — the official SDK, the "
        "in-cluster service account token, and port 6443 with client certs.",
}

# 分类页描述。分类页自己的 page-desc 很短（就一句话），
# 但 description 太短在搜索结果里没信息量，所以这里单独写长一点的版本。
CATEGORY_DESC = {
    "docker": "Running services in containers — OpenLDAP, Elasticsearch, "
              "Redis Cluster, and Keepalived, with the compose files and gotchas.",
    "kubernetes": "Container orchestration, cluster setup, and the API — "
                  "containerd, RKE2 high availability, ECR image pulls, metrics.",
    "troubleshooting": "Things that broke, and what actually fixed them. "
                       "Production incidents and the fix that held.",
    "networking": "Web servers, load balancing, and DNS — Nginx tuning, "
                  "LVS and Keepalived, BIND with a MySQL backend, redirects.",
    "storage": "Distributed filesystems and repository maintenance — "
               "GlusterFS, and pruning large files out of GitLab.",
    "systems": "Linux internals, virtualisation, and certificates — "
               "system tuning, KVM guests, and Let's Encrypt with acme.sh.",
    "other": "Everything that does not fit elsewhere — ClamAV, "
             "Redis tuning, and other Linux notes.",
}

CATEGORY_DIRS = list(CATEGORY_DESC)

START = "<!-- seo:start -->"
END = "<!-- seo:end -->"


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


def text_of(fragment):
    """把一段 HTML 变成纯文本。

    行内 <code> / <a> / <strong> 是句子的一部分，直接换成空格会留下
    「the credential you get from , and」这种破洞。所以先把行内标签
    整个抹掉（不留空格），再把块级标签换成空格。
    """
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    # 行内标签：直接删除，不补空格
    s = re.sub(r"</?(code|a|strong|em|b|i|span|sup|sub|kbd|var|samp)\b[^>]*>",
               "", s, flags=re.I)
    # 剩余块级标签：换成空格
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = collapse(s)
    # 收尾：标点前不留空格，括号内不留空格
    s = re.sub(r"\s+([,.;:!?%)\]])", r"\1", s)
    s = re.sub(r"([(\[])\s+", r"\1", s)
    s = re.sub(r"\s+(-|—|·)\s+", r" \1 ", s)
    return s.strip()


def body_of(raw):
    """取出 article-body 的 HTML（同 check.py 的逻辑）。"""
    key = '<div class="article-body">'
    i = raw.find(key)
    if i == -1:
        return ""
    start = i + len(key)
    depth = 1
    pos = start
    tag_re = re.compile(r"</?div\b[^>]*>")
    while depth > 0:
        m = tag_re.search(raw, pos)
        if not m:
            return ""
        depth += -1 if m.group(0).startswith("</") else 1
        pos = m.end()
    return raw[start:pos - len("</div>")]


def desc_source(body):
    """从正文里抽出适合做 description 的叙述性文本。

    难点：Hugo/Chroma 的代码块不是干净的 <pre><code>，而是套在
    <div class=highlight><div class=chroma><table class=lntable> 里，
    （还带行号那一列）。只删 <pre> 会把行号和表格结构留成碎片，
    产生「Pull an image: List images: Tag an image:」这种垃圾。

    所以策略是：先把代码块整体删掉，再删标题/图片/表格，
    最后只保留 <p> 段落。
    """
    # 1. 整体删除代码块容器（含 chroma 高亮块和裸 pre）
    s = re.sub(r"<div class=highlight\b.*?</div>\s*</div>", " ",
               body, flags=re.S | re.I)
    s = re.sub(r"<div class=\"highlight\".*?</div>\s*</div>", " ",
               s, flags=re.S | re.I)
    s = re.sub(r"<pre\b.*?</pre>", " ", s, flags=re.S | re.I)
    # 2. 删标题、图片、表格、列表（列表多是步骤罗列，做摘要不好读）
    s = re.sub(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<(table|figure|ol|ul)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<img\b[^>]*>", " ", s, flags=re.I)
    # 3. 剩下的段落取纯文本
    paras = re.findall(r"<p\b[^>]*>(.*?)</p>", s, re.S | re.I)
    if not paras:
        return ""
    texts = [text_of(p) for p in paras]
    # 丢掉过短的碎片（"Master node:"、"Reference:" 这类标签行）
    texts = [t for t in texts if len(t) >= 30]
    return collapse(" ".join(texts))


def meta_desc(raw, rel_dir):
    """优先级：固定文案 → 正文叙述段 → <title>。截到 155 字符左右。"""
    # 先按原样查，再按目录形式（补尾斜杠）查
    if rel_dir in STATIC_DESC:
        return STATIC_DESC[rel_dir]
    key = rel_dir.rstrip("/") + "/" if rel_dir else ""
    if key in STATIC_DESC:
        return STATIC_DESC[key]
    if rel_dir in POST_DESC:
        return POST_DESC[rel_dir]
    if rel_dir.rstrip("/") in CATEGORY_DESC:
        return CATEGORY_DESC[rel_dir.rstrip("/")]

    cand = desc_source(body_of(raw))
    if len(cand) >= 40:
        return trim_desc(cand)

    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    return trim_desc(_html.unescape(m.group(1)).strip() if m else SITE_NAME)


def trim_desc(s, limit=155):
    """截断到 limit 字符，尽量在词边界收尾。"""
    s = collapse(s)
    if len(s) <= limit:
        return s
    cut = s[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:.-") + "…"


def extract_date(raw):
    """从 article-meta 的 <time datetime="..."> 取日期。"""
    m = re.search(r'<time datetime="([^"]+)"', raw)
    return m.group(1) if m else ""


def extract_title(raw):
    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    return _html.unescape(m.group(1)).strip() if m else SITE_NAME


def esc_attr(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def seo_block(url, title, desc, iso_date, is_article, depth, image_url):
    """生成 SEO 标记块。depth=0 根目录，1 下一层。"""
    up = "../" if depth else ""
    lines = [START, ""]
    lines.append('<link rel="canonical" href="%s">' % url)
    lines.append('<meta name="description" content="%s">' % esc_attr(desc))
    lines.append("")
    # Open Graph
    lines.append('<meta property="og:type" content="%s">'
                 % ("article" if is_article else "website"))
    lines.append('<meta property="og:site_name" content="%s">' % SITE_NAME)
    lines.append('<meta property="og:title" content="%s">' % esc_attr(title))
    lines.append('<meta property="og:description" content="%s">' % esc_attr(desc))
    lines.append('<meta property="og:url" content="%s">' % url)
    if is_article and iso_date:
        lines.append('<meta property="article:published_time" content="%s">' % iso_date)
    lines.append('<meta property="og:image" content="%s">' % image_url)
    lines.append("")
    # Twitter
    lines.append('<meta name="twitter:card" content="summary_large_image">')
    lines.append('<meta name="twitter:title" content="%s">' % esc_attr(title))
    lines.append('<meta name="twitter:description" content="%s">' % esc_attr(desc))
    lines.append('<meta name="twitter:image" content="%s">' % image_url)
    lines.append("")
    lines.append('<link rel="alternate" type="application/atom+xml" '
                 'title="%s" href="%sfeed.xml">' % (SITE_NAME, up))
    # 结构化数据
    if is_article:
        ld = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": title,
            "description": desc,
            "url": url,
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "author": {"@type": "Person", "name": AUTHOR},
            "publisher": {"@type": "Organization", "name": SITE_NAME},
        }
        if iso_date:
            ld["datePublished"] = iso_date
    else:
        ld = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE + "/",
            "author": {"@type": "Person", "name": AUTHOR},
        }
        if url == SITE + "/":
            ld["potentialAction"] = {
                "@type": "SearchAction",
                "target": {"@type": "EntryPoint",
                           "urlTemplate": SITE + "/?q={search_term_string}"},
                "query-input": "required name=search_term_string",
            }
    lines.append("")
    lines.append('<script type="application/ld+json">')
    lines.append(json.dumps(ld, ensure_ascii=False, indent=2))
    lines.append("</script>")
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def inject(raw, block):
    """把块插到 </head> 前。已有标记块就替换，保证幂等。"""
    if START in raw and END in raw:
        pattern = re.compile(
            re.escape(START) + r".*?" + re.escape(END), re.S)
        return pattern.sub(lambda _: block, raw, count=1)
    i = raw.rfind("</head>")
    if i == -1:
        return raw
    # 确保前面留一个空行
    head = raw[:i].rstrip("\n")
    return head + "\n" + block + "\n" + raw[i:]


def main():
    pages = []   # (url, title, desc, iso, is_article)

    for dirpath, dirnames, filenames in os.walk(DIST):
        dirnames[:] = sorted(dirnames)
        for fn in sorted(filenames):
            if not fn.endswith(".html"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, DIST).replace("\\", "/")

            # 404 页不进 sitemap，但仍给它 canonical
            is_404 = rel == "404.html"

            # URL 规则：index.html → 目录形式；xxx.html → 原样
            if rel == "index.html":
                url_path = ""
                depth = 0
            elif rel.endswith("/index.html"):
                url_path = rel[: -len("index.html")]
                depth = 1
            else:
                url_path = rel
                depth = 0 if "/" not in rel else 1

            url = SITE + "/" + url_path
            raw = read(full)
            title = extract_title(raw)
            desc = meta_desc(raw, url_path)
            iso = extract_date(raw)

            # 判断是不是文章页：有 article-body 且不是首页/about/404/分类页
            in_category = url_path.rstrip("/") in CATEGORY_DESC
            is_article = (not is_404 and not in_category
                          and url_path.rstrip("/") not in ("", "about")
                          and 'class="article-body"' in raw)

            image = SITE + "/og-cover.png"
            block = seo_block(url, title, desc, iso, is_article, depth, image)
            new = inject(raw, block)
            if new != raw:
                write(full, new)

            if not is_404:
                pages.append((url, title, desc, iso, is_article, url_path))

    # ---------- sitemap.xml ----------
    # 文章页带 lastmod；首页排最前
    pages.sort(key=lambda p: (p[1] != "", p[5]))
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lastmod = datetime.date.today().isoformat()
    for url, title, desc, iso, is_article, _ in pages:
        sm.append("  <url>")
        sm.append("    <loc>%s</loc>" % url)
        sm.append("    <lastmod>%s</lastmod>" % (iso or lastmod))
        sm.append("    <changefreq>%s</changefreq>"
                  % ("monthly" if is_article else "weekly"))
        sm.append("    <priority>%s</priority>"
                  % ("0.8" if is_article else "0.6"))
        sm.append("  </url>")
    sm.append("</urlset>")
    write(os.path.join(DIST, "sitemap.xml"), "\n".join(sm) + "\n")

    # ---------- robots.txt ----------
    # pages.dev 是 Cloudflare 自动给的，跳不掉，只能让它别被索引
    robots = """User-agent: *
Allow: /

Sitemap: %s/sitemap.xml
""" % SITE
    write(os.path.join(DIST, "robots.txt"), robots)

    # ---------- feed.xml (Atom) ----------
    arts = [p for p in pages if p[4]]
    arts.sort(key=lambda p: p[3], reverse=True)
    updated = (arts[0][3] + "T00:00:00Z") if arts and arts[0][3] else \
              (datetime.datetime.now(datetime.timezone.utc)
               .strftime("%Y-%m-%dT%H:%M:%SZ"))
    fe = ['<?xml version="1.0" encoding="utf-8"?>',
          '<feed xmlns="http://www.w3.org/2005/Atom">',
          '  <title>%s</title>' % SITE_NAME,
          '  <subtitle>Notes on Linux, Kubernetes, and cloud-native infrastructure</subtitle>',
          '  <link href="%s/feed.xml" rel="self"/>' % SITE,
          '  <link href="%s/"/>' % SITE,
          '  <id>%s/</id>' % SITE,
          '  <updated>%s</updated>' % updated,
          '  <author><name>%s</name></author>' % AUTHOR]
    for url, title, desc, iso, _, _ in arts:
        fe.append("  <entry>")
        fe.append("    <title>%s</title>" % esc_attr(title))
        fe.append('    <link href="%s"/>' % url)
        fe.append("    <id>%s</id>" % url)
        if iso:
            fe.append("    <updated>%sT00:00:00Z</updated>" % iso)
        fe.append("    <summary>%s</summary>" % esc_attr(desc))
        fe.append("  </entry>")
    fe.append("</feed>")
    write(os.path.join(DIST, "feed.xml"), "\n".join(fe) + "\n")

    n_art = len(arts)
    n_all = len(pages)
    print("  SEO: %d 个页面注入标签" % n_all)
    print("  SEO: sitemap.xml (%d 条) / robots.txt / feed.xml (%d 篇)"
          % (n_all, n_art))


if __name__ == "__main__":
    main()
