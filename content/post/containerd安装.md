---
title: "Containerd安装"
date: 2023-03-01T17:44:11+08:00
draft: false
tags: ["container"] 
---

1、下载依赖安装包

```bash
wget https://github.com/containerd/containerd/releases/download/v1.6.4/cri-containerd-cni-1.6.4-linux-amd64.tar.gz
# 如果无法访问github可以使用下面地址
# wget https://download.fastgit.org/containerd/containerd/releases/download/v1.6.4/cri-containerd-cni-1.6.4-linux-amd64.tar.gz
```

2、解压

```bash
tar -C / -xzf cri-containerd-cni-1.6.4-linux-amd64.tar.gz
```

3、添加配置文件：

默认配置文件为 `/etc/containerd/config.toml`，我们可以通过如下所示的命令生成

```bash
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
```

4、启动containerd

```bash
systemctl enable containerd --now
```

5、验证containerd

```bash
# ctr version
Client:
  Version:  v1.6.4
  Revision: 72cec4be58a9eb6b2910f5d10f1c01ca47d231c0
  Go version: go1.16.6

Server:
  Version:  v1.6.4
  Revision: 72cec4be58a9eb6b2910f5d10f1c01ca47d231c0
  UUID: 38613830-5cd0-4bc4-81b4-2bcdced721d3
```