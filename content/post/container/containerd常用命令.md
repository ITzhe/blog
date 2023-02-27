---
title: "Containerd常用命令"
date: 2023-02-27T16:03:31+08:00
slug: "Hugo Slug"
draft: true
---

拉取镜像

```bash
ctr image pull docker.io/library/nginx:latest
```

查看容器

    ctr image ls -q

**创建**容器

    ctr c create docker.io/library/nginx:latest nginx

**启动**容器

    ctr task start -d nginx

直接启动容器（创建容器+启动容器）

    ctr run -d  --net-host nginx bash

查看容器状态

    ctr task ls

进入容器

    ctr task exec -t --exec-id 0 nginx /bin/bash

停止容器

    ctr task kill nginx

暂停容器

    ctr task pause nginx
