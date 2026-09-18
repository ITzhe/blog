---
title: "The Difference a Trailing Slash Makes in Nginx"
date: 2019-03-02T17:44:11+08:00
draft: false
slug: "nginx-trailing-slash"
tags: ["Nginx"]
---

There are two places a trailing slash matters:

1. After a `location` rule;
2. After `proxy_pass`.

Test URL: `https://www.xxxx.com/minio/ucenter/imgs/885058fa-dff6-4d60-875d-bb7dd2098ce9.png`

For `location`, the first case:

```bash
    location /minio/ {
        proxy_pass http://minio/;
    }
```

Conclusion: with or without the slash on `location` makes no difference.

---

Second case, variant 1:

```bash
    location /minio/ {
        proxy_pass http://minio/;
    }
```

The backend address actually requested: `127.0.0.1:9000/ucenter/imgs/885058fa-dff6-4d60-875d-bb7dd2098ce9.png`

Second case, variant 2:

```bash
    location /minio/ {
        proxy_pass http://minio;
    }
```

The backend address actually requested: `127.0.0.1:9000/minio/ucenter/imgs/885058fa-dff6-4d60-875d-bb7dd2098ce9.png`

Conclusion: a trailing slash on `proxy_pass` strips the `location` path prefix; without it, the `location` prefix is preserved.
