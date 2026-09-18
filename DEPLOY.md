# 部署到 Cloudflare Pages

本站已经不再是 Hugo 项目，而是一套**纯静态 HTML** 文件，全部放在 `dist/` 目录。
不需要任何构建命令，也不需要安装任何环境——Cloudflare 直接把 `dist/` 里的文件
发出去就行。

---

## 一、项目现状

```
blog/
├── dist/                 ← 网站本体，要部署的就是这个目录
│   ├── index.html        首页（20 篇文章列表）
│   ├── about/            关于页
│   ├── p/                文章页，每篇一个目录
│   │   └── nginx-tuning/index.html
│   ├── tags/             标签页
│   ├── style.css         全站样式（唯一的样式文件）
│   ├── 404.html          找不到页面时显示
│   ├── _headers          Cloudflare 响应头配置
│   ├── _redirects        Cloudflare 跳转规则
│   ├── robots.txt
│   └── sitemap.xml
├── check.py              体检工具：改完跑一次，检查有没有弄坏
└── .snapshot.json        内容快照，由 check.py 维护（要提交）
```

网站地址结构保持不变：`https://www.caizhe.org/p/nginx-tuning/` 这类老链接
**继续有效**，搜索引擎已收录的地址不会失效。

---

## 二、第一次部署（在 Cloudflare 网页上操作）

### 1. 建项目

Cloudflare 控制台 → **Workers & Pages** → **Create** → **Pages** →
**Connect to Git** → 选中你的仓库 `ITzhe/blog`。

### 2. 构建设置（关键，别填错）

| 设置项 | 填什么 |
| --- | --- |
| Production branch | `main` |
| Framework preset | **None**（不要选 Hugo！） |
| Build command | **留空** |
| Build output directory | `dist` |
| Root directory | **留空** |

因为没有构建步骤，环境变量那一栏**什么都不用填**。之前用的
`HUGO_VERSION`、`HUGO_ENV` 之类全部不需要了。

### 3. 保存并部署

点 **Save and Deploy**，等一两分钟。第一次会给出一个
`xxx.pages.dev` 的临时地址，可以先点开看看是否正常。

### 4. 绑定自己的域名

项目里 → **Custom domains** → **Set up a custom domain** → 填 `www.caizhe.org`。

- 如果域名就在 Cloudflare 上托管，会自动加好解析记录，无需手动操作。
- 如果是别处买的域名，按提示去域名商那边加一条 CNAME 指向
  `你的项目名.pages.dev`。

**注意 `www` 与裸域的关系**：`_redirects` 里已经写了「`caizhe.org` 跳转到
`www.caizhe.org`」的规则。为避免重复跳转导致循环，建议在这个 Pages 项目里
只绑定 `www.caizhe.org`，让裸域通过 Cloudflare 的 **Redirect Rules**
（或 DNS 页面的重定向功能）跳到 www。

---

## 三、以后怎么改内容

现在 `dist/` 里的 HTML 就是网站本体，**直接改 HTML** 就行。

### 改错字、改命令、调段落

打开 `dist/p/文章名/index.html`，正文都在这一行下面：

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

改完保存，提交并推送到 GitHub：

```bash
git add -A
git commit -m "更新 nginx-tuning 内容"
git push
```

Cloudflare 会自动重新部署，一两分钟后线上就是新的。

### 改完一定要跑一遍体检

**这是最重要的一条。** 手改 HTML 很容易弄坏标签，导致页面错乱。改完请运行：

```bash
python check.py
```

它会检查五件事：

1. **固定文件** —— `style.css`、`404.html`、`_redirects` 等是否都还在
2. **文章结构** —— 20 篇是否都有标题、正文区；HTML 标签是否配对
3. **链接** —— 有没有断链，页内跳转锚点是否还有效
4. **变化** —— 和上次相比，哪些文章的正文被改了、改了多少字
5. **总览** —— 文章数、总字数、文件数

正常时最后一行是「一切正常 ✓」，退出码 0。有问题会列出具体位置，
退出码 1，并提示你用 `git checkout -- dist/` 撤销。

> **举例**：如果你不小心删掉一个 `</div>`，体检会报
> 「标签嵌套错误：`</header>` 之前的标签没有关闭」，并指出是哪篇文章。

### 想加一篇新文章

1. 复制一个现有目录，比如复制 `dist/p/clamav/` 改名为 `dist/p/新文章名/`
2. 改 `index.html` 里的标题、日期、正文
3. 在 `dist/index.html` 的列表里加一行：

   ```html
   <li><time datetime="2026-09-18">Sep 18, 2026</time><a href="p/新文章名/">文章标题</a></li>
   ```

4. 在 `dist/sitemap.xml` 里加一行 `<url><loc>https://www.caizhe.org/p/新文章名/</loc></url>`

### 想改样式

只改 `dist/style.css` 一个文件，全站生效。颜色、宽度、字号都在文件顶部的
`:root { ... }` 里，改那里最省事。深色模式的配色在下面的
`@media (prefers-color-scheme: dark)` 里。

---

## 四、常见问题

**问：`check.py` 里的 `.snapshot.json` 是什么？**

答：是内容快照，记录每篇文章正文的指纹和字数。每次运行 `check.py` 都会更新，
用来对比这次改了哪些文章。**这个文件要提交到 git**，删掉它只是让下一次运行
变成「第一次运行」，不影响网站本身。

**问：我不小心删了 dist 里的东西怎么办？**

答：用 git 找回。查看历史：

```bash
git log --oneline
```

只需要撤销未提交的改动：

```bash
git checkout -- dist/
```

或者恢复到某个历史版本的文件：

```bash
git checkout 提交号 -- dist/文件名
```

**问：我想回到 Hugo 时代看看？**

答：迁移前的完整状态保存在 git 标签 `hugo-final` 里：

```bash
git checkout hugo-final     # 切到旧版本（只读，不要在这上面改）
git checkout main           # 看完切回来
```

**问：以后想加回搜索、归档这些页面怎么办？**

答：这些页面当初被精简掉了。如果确实需要，最简单的方式是手写一个静态页面
放进 `dist/`，然后在 `dist/index.html` 的导航里加个链接。不需要重新装 Hugo。

---

## 五、迁移前的老链接

以下旧地址都已配好 301 跳转，会自动指向新地址：

- 中文文章地址（如 `/p/nginx优化/`）→ 对应英文地址
- `/关于/` → `/about/`
- 语言前缀 `/en/`、`/zh-cn/`、`/ar/` → 去掉前缀
- Hugo 自动生成的 `/archives/`、`/search/`、`/page/2/` 等 → 首页

规则写在 `dist/_redirects` 里，Cloudflare 会自动识别。规则是**从上到下
顺序匹配、第一条生效**，所以不要随意调整顺序，也不要在末尾之外插入新规则。
