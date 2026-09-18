# -*- coding: utf-8 -*-
"""逐篇比对 Hugo 产物与纯静态产物的正文，确认一个字都没少。"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PUBLIC = ROOT / "public"
DIST = ROOT / "dist"


def extract(path, key, tag):
    """从 key 之后开始，找到配对的 </tag> 为止。"""
    raw = path.read_text(encoding="utf-8")
    i = raw.find(key)
    if i == -1:
        return None
    start = i + len(key)
    depth = 1
    pos = start
    tag_re = re.compile(rf"</?{tag}\b[^>]*>")
    while depth > 0:
        m = tag_re.search(raw, pos)
        if not m:
            return None
        depth += -1 if m.group(0).startswith("</") else 1
        pos = m.end()
    return raw[start:pos - len(f"</{tag}>")]


def norm(s):
    """归一化：去掉所有标签、空白、HTML 实体差异，只留可见文字。"""
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    s = re.sub(r"\s+", "", s)
    return s


def main():
    slugs = sorted(p.name for p in (DIST / "p").iterdir() if p.is_dir())
    bad = []
    total_src = total_new = 0
    print(f"{'文章':<34} {'原文字':>8} {'新文字':>8}  结果")
    print("-" * 68)
    for slug in slugs:
        a = extract(PUBLIC / "p" / slug / "index.html",
                    "<section class=article-content>", "section")
        b = extract(DIST / "p" / slug / "index.html",
                    '<div class="article-body">', "div")
        if a is None or b is None:
            bad.append((slug, "找不到正文"))
            print(f"{slug:<34} {'-':>8} {'-':>8}  ✗ 找不到正文")
            continue
        na, nb = norm(a), norm(b)
        total_src += len(na)
        total_new += len(nb)
        if na == nb:
            print(f"{slug:<34} {len(na):>8} {len(nb):>8}  ✓")
        else:
            # 找出第一处差异，方便定位
            k = 0
            while k < min(len(na), len(nb)) and na[k] == nb[k]:
                k += 1
            bad.append((slug, f"第 {k} 字起不同"))
            print(f"{slug:<34} {len(na):>8} {len(nb):>8}  ✗ 第 {k} 字起不同")
            print(f"    原文: ...{na[max(0,k-40):k+60]}")
            print(f"    新文: ...{nb[max(0,k-40):k+60]}")
    print("-" * 68)
    print(f"原文字符合计 {total_src} / 新文字符合计 {total_new}")
    if bad:
        print(f"\n有 {len(bad)} 篇存在问题：")
        for s, r in bad:
            print(f"  - {s}: {r}")
        sys.exit(1)
    else:
        print("\n全部 20 篇正文逐字一致，无内容丢失。")


if __name__ == "__main__":
    main()
