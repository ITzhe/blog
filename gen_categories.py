# -*- coding: utf-8 -*-
"""
生成分类页 /<slug>/index.html，并重写首页。

分类定义是唯一事实来源，改分类只需要改下面的 CATEGORIES。
正文内容（article-body）绝对不碰，只动首页和新建分类页。
"""
import os
import re
import sys

DIST = "dist"

# 分类定义：slug -> (英文名, 描述, [文章目录...])
CATEGORIES = [
    ("docker", "Docker", "Running services in containers.",
     ["docker-openldap", "docker-elasticsearch", "docker-redis-cluster", "docker-keepalived"]),
    ("kubernetes", "Kubernetes", "Container orchestration, cluster setup, and the API.",
     ["containerd-install", "containerd-commands", "kubernetes-1-22-ha-install",
      "kubernetes-api-calls", "rke2-ha-install", "ecr-image-pull-secret"]),
    ("troubleshooting", "Troubleshooting", "Things that broke, and what actually fixed them.",
     ["vault-dynamic-db-creds"]),
    ("networking", "Networking", "Web servers, load balancing, and DNS.",
     ["nginx-tuning", "nginx-trailing-slash", "lvs-keepalived", "bind-dlz", "301-vs-302-redirect"]),
    ("storage", "Storage", "Distributed filesystems and repository maintenance.",
     ["glusterfs-distributed-storage", "gitlab-purge-large-files"]),
    ("systems", "Systems", "Linux internals, virtualisation, and certificates.",
     ["linux-system-tuning", "kvm-virtual-machines", "letsencrypt-acme-sh"]),
    ("other", "Other", "Everything that does not fit elsewhere.",
     ["clamav", "redis-tuning"]),
]


def read_html(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_html(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def extract_title(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return m.group(1).strip() if m else "(untitled)"


def extract_date(html):
    """从 article-meta 里取 <time datetime="...">"""
    m = re.search(r'<time datetime="([^"]+)">([^<]*)</time>', html)
    if m:
        return m.group(1), m.group(2).strip()
    # 退路：从正文里找第一个时间戳
    m = re.search(r'<time[^>]*datetime="([^"]+)"[^>]*>([^<]*)</time>', html)
    if m:
        return m.group(1), m.group(2).strip()
    return "", ""


def article_body(html):
    m = re.search(r'<div class="article-body">', html)
    if not m:
        return ""
    start = m.end()
    depth = 1
    pos = start
    for tm in re.finditer(r"<(/?)div\b[^>]*>", html[start:]):
        if tm.group(1) == "":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                pos = start + tm.start()
                break
    return html[start:pos]


def slug_of(path):
    return os.path.basename(os.path.dirname(path))


# ---------- 收集文章元数据 ----------
posts = {}
for cat_slug, cat_name, cat_desc, dirs in CATEGORIES:
    for d in dirs:
        p = os.path.join(DIST, d, "index.html")
        if not os.path.exists(p):
            sys.exit("缺少文章: %s" % p)
        html = read_html(p)
        dt, dtext = extract_date(html)
        posts[d] = {
            "dir": d,
            "title": extract_title(html),
            "iso": dt,
            "date": dtext,
            "cat": cat_slug,
            "cat_name": cat_name,
        }

# 校验：dist 下的文章目录必须都被分类覆盖
all_dirs = {d for d in os.listdir(DIST)
            if os.path.isdir(os.path.join(DIST, d)) and d != "about"}
# 分类页自己也是目录，排除掉
all_dirs -= {c[0] for c in CATEGORIES}
missing = all_dirs - set(posts)
if missing:
    sys.exit("以下文章没有被分类: %s" % sorted(missing))
extra = set(posts) - all_dirs
if extra:
    sys.exit("分类里引用了不存在的文章: %s" % sorted(extra))

print("文章 %d 篇，全部分类完毕" % len(posts))


def head(title, depth):
    """depth=0 首页（在 dist 根），depth=1 子目录页（分类页/文章页）"""
    up = "../" if depth else ""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="%sstyle.css">
<link rel="icon" href="%sfavicon.ico">
</head>
""" % (title, up, up)


def header_html(depth=0):
    """分类页和文章页都在 dist 下一层，所以用 ../ 回根目录"""
    up = "../" if depth else "./"
    return """<header class="site-header">
  <div class="wrap">
    <a class="site-title" href="%s">caizhe.org</a>
    <nav class="site-nav">
      <a href="%s">Home</a>
      <a href="%sabout/">About</a>
      <a href="https://github.com/ITzhe/blog">GitHub</a>
    </nav>
  </div>
</header>
""" % (up, up, up)


def footer_html(depth=0):
    up = "../" if depth else "./"
    return """<footer class="site-footer">
  <div class="wrap">
    &copy; caizhe &middot; <a href="%sabout/">About</a> &middot; <a href="https://github.com/ITzhe/blog">GitHub</a>
  </div>
</footer>
""" % up


# ---------- 生成分类页 ----------
for cat_slug, cat_name, cat_desc, dirs in CATEGORIES:
    items = sorted((posts[d] for d in dirs), key=lambda p: p["iso"], reverse=True)
    rows = "\n".join(
        '      <li><time datetime="%s">%s</time><a href="../%s/">%s</a></li>'
        % (p["iso"], p["date"], p["dir"], p["title"])
        for p in items
    )
    page = head("%s &middot; caizhe.org" % cat_name, 1)
    page += "<body>\n"
    page += header_html(1)
    page += '<main class="wrap">\n'
    page += '  <h1 class="page-title">%s</h1>\n' % cat_name
    page += '  <p class="page-desc">%s</p>\n' % cat_desc
    page += '  <ul class="post-list">\n%s\n  </ul>\n' % rows
    page += '  <p class="back-link"><a href="../">&larr; All posts</a></p>\n'
    page += "</main>\n"
    page += footer_html(1)
    page += "</body>\n</html>\n"
    write_html(os.path.join(DIST, cat_slug, "index.html"), page)
    print("  生成 %s/  (%d 篇)" % (cat_slug, len(items)))

# ---------- 生成搜索索引 ----------
def unescape(s):
    """标题在 HTML 里是转义过的（如 Let&#x27;s），索引用明文即可。"""
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#x27;", "'"), ("&#39;", "'")):
        s = s.replace(a, b)
    return s


search_data = [
    {"t": unescape(p["title"]), "u": "%s/" % p["dir"], "c": p["cat_name"],
     "d": p["date"], "y": p["iso"][:4]}
    for p in sorted(posts.values(), key=lambda x: x["iso"], reverse=True)
]
import json as _json
write_html(os.path.join(DIST, "search-index.json"),
           _json.dumps(search_data, ensure_ascii=False, separators=(",", ":")) + "\n")
print("  生成 search-index.json  (%d 条)" % len(search_data))

# ---------- 重写首页 ----------
cards = []
for cat_slug, cat_name, cat_desc, dirs in CATEGORIES:
    cards.append(
        '      <a class="cat-card" href="%s/">\n'
        '        <span class="cat-name">%s</span>\n'
        '        <span class="cat-desc">%s</span>\n'
        '        <span class="cat-count">%d post%s</span>\n'
        '      </a>'
        % (cat_slug, cat_name, cat_desc, len(dirs), "" if len(dirs) == 1 else "s")
    )
n_posts = sum(len(c[3]) for c in CATEGORIES)

SEARCH_JS = """<script>
(function () {
  var box = document.getElementById('q');
  var out = document.getElementById('results');
  var cards = document.getElementById('cats');
  if (!box || !out || !cards) return;
  var data = null, loading = false;

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function render(list) {
    if (!list.length) {
      out.innerHTML = '<p class="no-hit">Nothing found.</p>';
    } else {
      out.innerHTML = '<ul class="post-list">' + list.map(function (p) {
        return '<li><time>' + esc(p.d) + '</time>' +
               '<a href="' + esc(p.u) + '">' + esc(p.t) + '</a>' +
               '<a class="tag" href="' + esc(p.c.toLowerCase()) + '/">' +
               esc(p.c) + '</a></li>';
      }).join('') + '</ul>';
    }
    out.hidden = false;
    cards.hidden = true;
  }

  function clear() {
    out.hidden = true;
    out.innerHTML = '';
    cards.hidden = false;
  }

  box.addEventListener('input', function () {
    var q = box.value.trim().toLowerCase();
    if (!q) { clear(); return; }
    if (data) { filter(q); return; }
    if (loading) return;
    loading = true;
    fetch('search-index.json').then(function (r) { return r.json(); })
      .then(function (d) { data = d; loading = false; filter(box.value.trim().toLowerCase()); })
      .catch(function () { loading = false; });
  });

  function filter(q) {
    render(data.filter(function (p) {
      return (p.t + ' ' + p.c + ' ' + p.y).toLowerCase().indexOf(q) !== -1;
    }));
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && box.value) { box.value = ''; clear(); box.blur(); }
  });
})();
</script>
"""

index = head("caizhe.org", 0)
index += "<body>\n"
index += header_html(0)
index += '<main class="wrap">\n'
index += '  <form class="search" role="search" onsubmit="return false">\n'
index += '    <input id="q" type="search" placeholder="Search %d posts&hellip;" ' % n_posts
index += 'autocomplete="off" spellcheck="false" aria-label="Search posts">\n'
index += "  </form>\n"
index += '  <section class="cats" id="cats">\n'
index += "\n".join(cards) + "\n"
index += "  </section>\n"
index += '  <section id="results" hidden></section>\n'
index += "</main>\n"
index += footer_html(0)
index += SEARCH_JS
index += "</body>\n</html>\n"
write_html(os.path.join(DIST, "index.html"), index)
print("  重写 index.html  (%d 篇，%d 个分类)" % (n_posts, len(CATEGORIES)))
print("完成")
