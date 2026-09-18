# 部署与维护说明

这是一个**纯静态 HTML 网站**：只有文章、首页、关于页。

没有构建步骤，没有框架，没有需要安装的环境。
`dist/` 就是网站本体，Cloudflare 直接把里面的文件发出去。

---

## 一、站点结构

```
blog/
├── dist/                  ← 网站本体，部署目录填 dist
│   ├── index.html         首页（20 篇文章列表）
│   ├── 404.html           找不到页面时显示
│   ├── style.css          全站唯一的样式文件
│   ├── favicon.ico        标签页图标
│   ├── about/
│   │   └── index.html     关于页
│   ├── nginx-tuning/
│   │   └── index.html     文章页，每篇一个目录
│   ├── ...                另外 19 篇文章
├── check.py               体检工具
└── .snapshot.json         内容快照（check.py 用，要提交）
```

**文章地址就是目录名**，比如 `dist/nginx-tuning/index.html` 对应
`https://www.caizhe.org/nginx-tuning/`。

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

它检查六件事：

1. **固定文件** —— `index.html`、`style.css`、`404.html` 等是否都在
2. **老站残留** —— 是否混入了 `sitemap.xml`、`_redirects`、`tags/` 之类
   这个网站不需要的文件
3. **文章结构** —— 每篇是否都有标题、正文区；HTML 标签是否配对
4. **链接** —— 有没有断链，页内跳转锚点是否有效
5. **不该出现的内容** —— 是否混入了 SEO 标签或指向已删除标签页的链接
6. **内容变化** —— 和上次相比，哪些文章的正文被改了、改了多少字

正常时最后一行是「一切正常 ✓」，退出码 0。有问题会列出具体位置并提示
用 `git checkout -- dist/` 撤销。

> **举例**：如果你不小心删掉一个 `</div>`，体检会报
> 「标签嵌套错误：`</header>` 之前的标签没有关闭」，并指出是哪篇文章。

### 加一篇新文章

1. 复制一个现有目录，比如复制 `dist/clamav/`，改名为 `dist/新文章名/`
   （目录名就是 URL，用英文小写加连字符）
2. 改 `index.html` 里的标题、日期、正文
3. 在 `dist/index.html` 的文章列表里加一行：

   ```html
   <li><time datetime="2026-09-18">Sep 18, 2026</time><a href="新文章名/">文章标题</a></li>
   ```

   放在合适的位置（列表是按日期倒序的）。
4. 跑 `python check.py` 确认没弄坏。

### 改样式

只改 `dist/style.css` 一个文件，全站生效。

颜色、宽度、字号都在文件顶部的 `:root { ... }` 里。
深色模式的配色在下面的 `@media (prefers-color-scheme: dark)` 里。

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
