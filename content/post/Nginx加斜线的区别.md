---
title: "Nginx 加斜线的区别"
date: 2019-03-02T17:44:11+08:00
draft: false
tags: ["Nginx"] 
---

加斜线分为两种：

1、localtion 规则后面加/

2、proxy_pass后面加/

测试的URL:https://www.xxxx.com/minio/ucenter/imgs/885058fa-dff6-4d60-875d-bb7dd2098ce9.png

localtion 第一种情况：

```bash
    location /minio/ {
        proxy_pass http://minio/;
    }
```

结论：加/或者不加/没有区别。

---
第二种情况1：

```bash
    location /minio/ {
        proxy_pass http://minio/;
    }
```

实际访问的后端地址：127.0.0.1:9000/ucenter/imgs/885058fa-dff6-4d60-875d-bb7dd2098ce9.png

第二种情况2：

```bash
    location /minio/ {
        proxy_pass http://minio;
    }
```

实际访问的后端地址：127.0.0.1:9000/minio/ucenter/imgs/885058fa-dff6-4d60-875d-bb7dd2098ce9.png

结论：proxy_pass 后面加了斜线，会把location部分的路径去掉，反之不加斜线，会保留location部分的路径

---
