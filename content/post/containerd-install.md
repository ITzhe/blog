---
title: "Installing containerd"
date: 2023-03-01T17:44:11+08:00
draft: false
slug: "containerd-install"
tags: ["container"]
---

1. Download the dependency package:

```bash
wget https://github.com/containerd/containerd/releases/download/v1.6.4/cri-containerd-cni-1.6.4-linux-amd64.tar.gz
# If you cannot reach GitHub, use this mirror instead
# wget https://download.fastgit.org/containerd/containerd/releases/download/v1.6.4/cri-containerd-cni-1.6.4-linux-amd64.tar.gz
```

2. Extract:

```bash
tar -C / -xzf cri-containerd-cni-1.6.4-linux-amd64.tar.gz
```

3. Add the configuration file:

The default config file is `/etc/containerd/config.toml`, generated with the command below.

```bash
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
```

4. Start containerd:

```bash
systemctl enable containerd --now
```

5. Verify containerd:

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
