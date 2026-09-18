# 部署到 Cloudflare Pages

本站是 Hugo 静态站点，由 Cloudflare Pages 直接从 GitHub 仓库 `ITzhe/blog` 构建，
不需要维护任何 CI 工作流，也不把构建产物提交到仓库。

## 一次性配置

1. 登录 Cloudflare 控制台，进入 **Workers 和 Pages** → **创建** →
   **Pages** → **连接到 Git**。
2. 授权 Cloudflare 访问 GitHub，选择 `ITzhe/blog` 仓库。
3. 按下表填写构建配置：

   | 配置项 | 填写内容 |
   | --- | --- |
   | 生产分支 | `main` |
   | 框架预设 | `Hugo` |
   | 构建命令 | `hugo --gc --minify` |
   | 构建输出目录 | `public` |
   | 根目录 | *留空* |

4. 在 **环境变量（高级）** 中添加：

   | 变量名 | 值 |
   | --- | --- |
   | `HUGO_VERSION` | `0.146.0` |
   | `HUGO_ENV` | `production` |
   | `HUGO_ENABLEGITINFO` | `true` |

   `HUGO_VERSION` **必须设置**。Cloudflare 自带的 Hugo 版本通常偏老，而 Stack
   主题需要 **extended 版本**才能编译 SCSS。只要你固定了版本号，Cloudflare
   会自动安装对应的 extended 构建。

   > 关于版本号：主题原版代码用的 `resources.ToCSS` 和 `.Site.LastChange`
   > 在新版 Hugo 里已被移除，我已在站点层覆盖了这几个模板文件做兼容。
   > `0.146.0` 是本地验证通过的版本，直接照填即可。

5. 点击 **保存并部署**。

## 绑定自定义域名

1. 进入该 Pages 项目，选择 **自定义域** → **设置自定义域**。
2. 先添加 `www.caizhe.org`，再添加 `caizhe.org`，让两个域名都能访问。
3. 把 `caizhe.org` 设置为跳转到 `www.caizhe.org`（或反过来也行，但**必须
   选定一个主域名并保持一致**）。`_redirects` 文件里已经把裸域统一跳转到
   `www.caizhe.org`，与 `config.yaml` 中的 `baseurl` 保持一致。
4. 如果你的 DNS 本来就托管在 Cloudflare，解析记录会自动创建；否则按提示手动
   添加 Cloudflare 给出的 `CNAME` 记录。
5. 等证书签发完成（通常几分钟），再到 SSL/TLS → 边缘证书里开启
   **始终使用 HTTPS**。

## 后续的构建流程

- 每次推送到 `main` 分支，都会触发一次生产构建并自动部署。
- 推送到其它分支、以及每个 Pull Request，都会生成独立的预览地址——
  合并前可以先检查翻译效果。
- 构建日志可以在控制台对应的部署记录里查看。

## 本地预览

```bash
# 在仓库根目录执行
hugo server --buildDrafts --disableFastRender
```

然后打开 <http://localhost:1313/>。

要本地生成一份生产构建：

```bash
hugo --gc --minify
# 产物输出到 ./public
```

## 注意事项

- `public/` 和 `resources/` 已加入 `.gitignore`，**不要提交**。Cloudflare 会
  自己构建站点，提交 `public/` 是导致内容过期或重复的常见原因。
- `static/_headers` 用来设置安全响应头，并对带指纹的静态资源启用长期缓存。
- `static/_redirects` 保留了迁移前所有旧的中文 URL 跳转规则。以后如果有文章的
  slug 变更，记得在这里补一条规则。
- 本站是纯英文单语站点。`config.yaml` 里没有 `languages` 配置块，所有内容都
  直接放在 `content/` 下，不需要按语言分子目录。
