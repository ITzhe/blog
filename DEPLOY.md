# 部署与维护说明

这是一个**纯静态 HTML 网站**：只有文章、首页、关于页。

没有构建步骤，没有框架，没有需要安装的环境。
`dist/` 就是网站本体，Cloudflare 直接把里面的文件发出去。

---

## 一、站点结构

```
blog/
├── dist/                  ← 网站本体，部署目录填 dist
│   ├── index.html         首页（只有分类卡片 + 搜索框）
│   ├── 404.html           找不到页面时显示
│   ├── style.css          全站唯一的样式文件
│   ├── favicon.ico        标签页图标
│   ├── og-cover.png       分享到微信/Twitter 时的预览图（1200x630）
│   ├── search-index.json  首页搜索用的静态索引
│   ├── sitemap.xml        给搜索引擎的页面清单（自动生成）
│   ├── robots.txt         爬虫规则（自动生成）
│   ├── feed.xml           RSS 订阅源（自动生成）
│   ├── about/
│   │   └── index.html     关于页
│   ├── docker/ kubernetes/ ...   分类页（7 个，自动生成）
│   ├── nginx-tuning/
│   │   └── index.html     文章页，每篇一个目录
│   └── ...                另外 22 篇文章
├── check.py               体检工具
├── gen_categories.py      生成分类页 + 首页 + 搜索索引
├── gen_seo.py             注入 SEO 标签 + 生成 sitemap/robots/feed
├── gen_og_cover.py        生成分享预览图 og-cover.png
└── .snapshot.json         内容快照（check.py 用，要提交）
```

**文章地址就是目录名**，比如 `dist/nginx-tuning/index.html` 对应
`https://www.caizhe.org/nginx-tuning/`。

### SEO 是自动的，不要手改

`canonical` / `description` / Open Graph / 结构化数据由 `gen_seo.py`
统一注入，包在 `<!-- seo:start -->` 和 `<!-- seo:end -->` 之间。

- **不要手工编辑那个标记块**，重跑脚本会被覆盖
- 重跑是**幂等**的，不会重复叠加标签
- `sitemap.xml`、`robots.txt`、`feed.xml` 都是生成的，不要手改
- **canonical 一律指向 `https://www.caizhe.org/`**：裸域已 301 到 www，
  而 `*.pages.dev` 是 Cloudflare 自动给的、跳不掉，只能靠 canonical 收敛

改完文章标题或正文后，重跑一次就能刷新 description：

```
python gen_categories.py     # 它会自动调用 gen_seo.py
```

想手写某篇文章的 description（自动摘的不满意时），
加到 `gen_seo.py` 的 `POST_DESC` 字典里，键是 `"<slug>/"`。

---

## 二、第一次部署（Cloudflare 网页操作）

### 1. 建项目

Cloudflare 控制台 → **Workers & Pages** → **Create** → **Pages** →
**Connect to Git** → 选中仓库 `ITzhe/blog`。

### 2. 构建设置

| 设置项 | 填什么 |
| --- | --- |
| Production branch | `main` |
| Framework preset | **None** |
| Build command | **留空** |
| Build output directory | `dist` |
| Root directory | **留空** |
| 环境变量 | **一个都不用填** |

### 3. 保存并部署

点 **Save and Deploy**，等一两分钟。

### 4. 绑定域名

项目里 → **Custom domains** → **Set up a custom domain** → 填 `www.caizhe.org`。

如果域名也在 Cloudflare 托管，解析会自动配好。

> 建议**只绑定 `www.caizhe.org`**。裸域 `caizhe.org` 可以在 Cloudflare 的
> Redirect Rules 里配一条跳转到 www，避免重复跳转。

---

## 三、怎么改内容

### 改错字、改命令、调段落

打开 `dist/<文章名>/index.html`，正文在 `<div class="article-body">` 里：

```html
    <div class="article-body">
    <p>
  这里是段落的文字。
</p>
<h2 id=某个锚点>
  这里是二级标题
</h2>
<pre><code>这里是代码块，不要改动里面的内容
</code></pre>
    </div>
```

改完保存，提交推送：

```bash
git add -A
git commit -m "更新 nginx-tuning"
git push
```

Cloudflare 会自动重新部署，一两分钟后线上生效。

### 改完一定要跑体检

**这是最重要的一条。** 手改 HTML 很容易弄坏标签：

```bash
python check.py
```

它检查这些事：

1. **固定文件** —— `index.html`、`style.css`、`404.html`、`sitemap.xml`、
   `robots.txt`、`feed.xml` 等是否都在
2. **老站残留** —— 是否混入了 `_redirects`、`tags/` 之类不需要的文件
3. **文章结构** —— 每篇是否都有标题、正文区；HTML 标签是否配对
4. **分类页** —— 分类页是否完整；每篇文章是否都被某个分类收录
5. **搜索索引** —— `search-index.json` 和文章是否一一对应
6. **链接** —— 有没有断链，页内跳转锚点是否有效
7. **不该出现的内容** —— 阿里云 OSS 图片残留、指向已删标签页的链接
8. **SEO 标签** —— 每页是否有 canonical / description / og / 结构化数据；
   canonical 是否指向 www 主域、是否重复；`sitemap.xml` 和 canonical
   是否对得上；`robots.txt` 是否声明了 Sitemap；`feed.xml` 是否是合法 XML
9. **内容变化** —— 和上次相比，哪些文章的正文被改了、改了多少字

正常时最后一行是「一切正常 ✓」，退出码 0。有问题会列出具体位置并提示
用 `git checkout -- dist/` 撤销。

> **举例**：如果你不小心删掉一个 `</div>`，体检会报
> 「标签嵌套错误：`</header>` 之前的标签没有关闭」，并指出是哪篇文章。

### 加一篇新文章

1. 复制一个现有目录，比如复制 `dist/clamav/`，改名为 `dist/新文章名/`
   （目录名就是 URL，用英文小写加连字符）
2. 改 `index.html` 里的标题、日期、正文
3. 在 `gen_categories.py` 的 `CATEGORIES` 里，把新目录名加到对应分类的列表里
4. 跑生成 + 体检：

   ```
   python gen_categories.py     # 重建分类页/首页/搜索索引，并注入 SEO 标签
   python check.py
   ```

**不用手动改首页列表** —— 首页只显示分类卡片，文章入口在分类页，
都由脚本生成。忘了第 3 步的话，`gen_categories.py` 和 `check.py`
都会报错拦住你（这是故意的）。

### 加一个新分类

要改两个文件，少改一个会踩坑：

1. `gen_categories.py` 的 `CATEGORIES` —— 生成分类页 + 首页卡片 + 搜索索引
2. `check.py` 的 `CATEGORY_DIRS` —— **漏改会把分类页当成文章去查正文，
   报一堆「没有正文区」的假错误**

如果想让这个分类页在搜索结果里有更好的 description，
再把它加到 `gen_seo.py` 的 `CATEGORY_DESC` 里。

### 改样式

只改 `dist/style.css` 一个文件，全站生效。

颜色、宽度、字号都在文件顶部的 `:root { ... }` 里。
深色模式的配色在下面的 `@media (prefers-color-scheme: dark)` 里。

> 站点标题统一用 `<a class="site-title">`，**不要包 `<h1>`** ——
> 文章页已经有 `<h1 class="article-title">`，再包一层会出现两个一级标题。

---

## 四、提交后要做的 SEO 动作（一次性）

代码里该有的都有了，但有两件事只能在网页上做：

1. **Google Search Console** —— 添加资源 `https://www.caizhe.org`，
   用 DNS 验证（Cloudflare 里加一条 TXT 记录即可），
   然后提交 `https://www.caizhe.org/sitemap.xml`
2. **Bing Webmaster Tools** —— 同上，可以从 Search Console 直接导入

提交后可以在「网址检查」里手动请求抓取首页，加速收录。

---

## 四、常见问题

**问：我不小心改坏了怎么办？**

答：用 git 撤销。

只撤销还没提交的改动：

```bash
git checkout -- dist/
```

如果已经提交了，先看历史：

```bash
git log --oneline
```

再恢复到某个版本的文件：

```bash
git checkout 提交号 -- dist/文件名
```

**问：`.snapshot.json` 是什么？**

答：内容快照，记录每篇文章正文的指纹和字数。每次运行 `check.py` 都会更新，
用来对比这次改了哪些文章。**这个文件要提交到 git**。删掉它只是让下次运行
变成「第一次运行」，不影响网站。

**问：文章里的图片在哪？**

答：托管在 **Cloudflare R2** 上，路径是 `images/ldap/`，
对外地址形如：

```
https://pub-b2701aab0ccd420d85467389867d17a8.r2.dev/images/ldap/1.png
```

只有 `docker-openldap` 那一篇有图，共 14 张（`1.png` ~ `12.png` 和两张
时间戳命名的截图）。

要换图片的话，在 R2 控制台上传新文件，然后在 HTML 里改 `src` 即可。
注意 R2 的 `r2.dev` 开发地址会拦截非浏览器的请求（比如脚本直接抓取会
返回 403），但浏览器访问完全正常，不影响网站。

**问：为什么没有 sitemap.xml、robots.txt、跳转规则？**

答：这是有意去掉的。这个网站是全新的，不需要讨好搜索引擎，
也不需要为旧地址做跳转。保持简单。

**问：想找回迁之前的 Hugo 版本？**

答：完整存档在 git 标签 `hugo-final` 里：

```bash
git checkout hugo-final     # 只读查看，不要在这上面改
git checkout main           # 看完切回来
```
