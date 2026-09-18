# -*- coding: utf-8 -*-
"""
把站点从 /p/<slug>/ 搬到 /<slug>/，并剥掉所有 SEO 相关的东西。

这是一个**一次性**脚本，跑完就可以删掉。

做三件事：
  1. dist/p/<slug>/  ->  dist/<slug>/
  2. 删掉 sitemap.xml、robots.txt、_redirects、_headers、tags/
  3. 剥掉页面里所有 SEO 痕迹：canonical、og:*、twitter:*、description meta

正文内容一个字都不动。
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
DIST = ROOT / "dist"


def move_posts():
    """把 dist/p/<slug>/ 搬到 dist/<slug>/。"""
    src = DIST / "p"
    if not src.is_dir():
        print("  dist/p/ 不存在，跳过")
        return
    moved = []
    for d in sorted(src.iterdir()):
        if not d.is_dir():
            continue
        target = DIST / d.name
        if target.exists():
            print(f"  跳过 {d.name}（目标已存在）")
            continue
        shutil.move(str(d), str(target))
        moved.append(d.name)
    # 收尾：干掉空的 p 目录
    try:
        src.rmdir()
        print(f"  已删除空的 dist/p/")
    except OSError:
        print(f"  dist/p/ 非空，残留内容：{list(src.iterdir())}")
    print(f"  搬移了 {len(moved)} 篇文章")


def remove_legacy_files():
    """删掉新网站不需要的文件。"""
    targets = ["sitemap.xml", "robots.txt", "_redirects", "_headers"]
    for name in targets:
        p = DIST / name
        if p.exists():
            p.unlink()
            print(f"  已删除 {name}")
    # tags 整个目录
    tags = DIST / "tags"
    if tags.is_dir():
        shutil.rmtree(tags)
        print("  已删除 tags/ 目录")


# 要整行删除的 head 标签
SEO_LINE_PATTERNS = [
    r'^\s*<link rel="canonical"[^>]*>\s*$',
    r'^\s*<meta name="description"[^>]*>\s*$',
    r'^\s*<meta property="og:[^"]*"[^>]*>\s*$',
    r'^\s*<meta name="twitter:[^"]*"[^>]*>\s*$',
    r'^\s*<meta name="keywords"[^>]*>\s*$',
    r'^\s*<meta name="author"[^>]*>\s*$',
]


def strip_seo(html_text):
    """去掉 SEO 相关的 head 标签。"""
    lines = html_text.split("\n")
    out = []
    for ln in lines:
        if any(re.match(p, ln) for p in SEO_LINE_PATTERNS):
            continue
        out.append(ln)
    return "\n".join(out)


def fix_links():
    """
    把页面里的站内链接从 /p/<slug>/ 改成 /<slug>/。
    涉及：首页列表、标签链接、导航、返回链接。
    """
    changed = 0
    for f in DIST.rglob("*.html"):
        raw = f.read_text(encoding="utf-8")
        orig = raw

        # 相对路径形式（文章页里的 href="../../p/xxx/" -> href="../../xxx/"）
        raw = re.sub(r'(href=")\.\./\.\./p/', r'\1../../', raw)
        raw = re.sub(r'(href=")p/', r'\1', raw)          # 首页列表
        # 绝对路径形式
        raw = re.sub(r'(href=")/p/', r'\1/', raw)
        raw = re.sub(r'(href=)/p/', r'\1/', raw)

        if raw != orig:
            f.write_text(raw, encoding="utf-8")
            changed += 1
    print(f"  修正了 {changed} 个文件里的站内链接")


def strip_seo_all():
    n = 0
    for f in DIST.rglob("*.html"):
        raw = f.read_text(encoding="utf-8")
        new = strip_seo(raw)
        if new != raw:
            f.write_text(new, encoding="utf-8")
            n += 1
    print(f"  清除了 {n} 个文件里的 SEO 标签")


def main():
    print("=" * 60)
    print("转换为全新网站结构")
    print("=" * 60)

    print("\n[1/4] 搬移文章目录")
    move_posts()

    print("\n[2/4] 删除老站遗留文件")
    remove_legacy_files()

    print("\n[3/4] 修正站内链接")
    fix_links()

    print("\n[4/4] 清除 SEO 标签")
    strip_seo_all()

    print("\n完成。")


if __name__ == "__main__":
    main()
