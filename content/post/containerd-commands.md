---
title: "Common containerd Commands"
date: 2023-03-02T17:44:11+08:00
draft: false
slug: "containerd-commands"
tags: ["container"]
---

## Images

Pull an image:

    ctr image pull docker.io/library/nginx:latest

List images:

    ctr image ls -q

Tag an image:

    ctr image tag docker.io/library/nginx:latest caizhe.org/library/nginx:latest

Remove an image:

    ctr images rm caizhe.org/library/nginx:latest

Mount an image to a local directory:

    ctr image mount docker.io/library/nginx:latest /mnt

Unmount:

    ctr image unmount /mnt

Export:

    ctr image export nginx.tar.gz docker.io/library/nginx:latest

Import:

    ctr i import nginx.tar.gz

Fixing the `ctr: content digest sha256:xxxxxx not found` error:

``` shell
Option 1:
    ctr image pull --platform amd64  docker.io/library/nginx:latest 
    ctr i export --platform amd64 nginx.tar.gz docker.io/library/nginx:latest
    ctr i import --platform amd64 nginx.tar.gz 
Option 2:
    ctr i pull --all-platforms docker.io/library/nginx:latest
    ctr i export --all-platforms nginx.tar.gz docker.io/library/nginx:latest
    ctr i import nginx.tar.gz
```
## Containers

**Create** a container:

    ctr container create docker.io/library/nginx:latest nginx

List containers:

    ctr container ls

Remove a container:

    ctr container rm nginx

**Start** a container:

    ctr task start -d nginx

Create and start a container in one step:

    ctr run -d  --net-host nginx bash

Check container status:

    ctr task ls

Enter a container:

    ctr task exec -t --exec-id 0 nginx /bin/bash

Stop a container:

    ctr task kill nginx

Pause a container:

    ctr task pause nginx

Check container resource usage:

    ctr task metrics nginx

## Namespaces

List namespaces:

    ctr ns ls

Create a namespace:

    ctr ns create test

Remove a namespace:

    ctr ns rm test

***

Tip: Docker's namespace is `moby`; Kubernetes' namespace is `k8s.io`.
