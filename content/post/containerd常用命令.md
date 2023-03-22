---
title: "Containerd常用命令"
date: 2023-03-02T17:44:11+08:00
draft: false
tags: ["container"] 
---

## 镜像

拉取镜像

    ctr image pull docker.io/library/nginx:latest

查看镜像

    ctr image ls -q

TAG标签

    ctr image tag docker.io/library/nginx:latest caizhe.org/library/nginx:latest

删除镜像

    ctr images rm caizhe.org/library/nginx:latest

挂载镜像到本地目录

    ctr image mount docker.io/library/nginx:latest /mnt

取消挂载

    ctr image unmount /mnt

导出

    ctr image export nginx.tar.gz docker.io/library/nginx:latest

导入

    ctr i import nginx.tar.gz

解决`ctr: content digest sha256:xxxxxx not found`的错误

``` shell
方法1：
    ctr image pull --platform amd64  docker.io/library/nginx:latest 
    ctr i export --platform amd64 nginx.tar.gz docker.io/library/nginx:latest
    ctr i import --platform amd64 nginx.tar.gz 
方法2：
    ctr i pull --all-platforms docker.io/library/nginx:latest
    ctr i export --all-platforms nginx.tar.gz docker.io/library/nginx:latest
    ctr i import nginx.tar.gz
```
## 容器

**创建**容器

    ctr container create docker.io/library/nginx:latest nginx

查看容器

    ctr container ls

删除容器

    ctr container rm nginx

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

查看容器资源使用情况

    ctr task metrics nginx

## 名称空间

查看名称空间

    ctr ns ls

创建名称空间

    ctr ns create test

删除名称空间

    ctr ns rm test

***

提示：docker的名称空间是moby，k8s的名称空间是k8s.io
