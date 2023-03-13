---
title: "Docker安装Keepalived"
date: 2023-03-13 T20:52:54+08:00
draft: false
tags: ["部署","docker"]
---


主节点：

```shell
[root@59-139 ~]# docker run -d --net=host --cap-add NET_ADMIN \
 -e KEEPALIVED_AUTOCONF=true                  \
 # 角色 \
 -e KEEPALIVED_STATE=MASTER                   \
 # 绑定的网卡 \
 -e KEEPALIVED_INTERFACE=ens33                 \
 # keep alive 通讯的标识ID \
 -e KEEPALIVED_VIRTUAL_ROUTER_ID=2            \
 # 广播地址 \
 -e KEEPALIVED_UNICAST_SRC_IP=192.168.59.139  \
 -e KEEPALIVED_UNICAST_PEER_0=192.168.59.140  \
 # 绑定的网卡 \
 -e KEEPALIVED_TRACK_INTERFACE_1=ens33         \
 # 虚拟VIP \
 -e KEEPALIVED_VIRTUAL_IPADDRESS_1="192.168.59.100/24 dev ens33" \
 arcts/keepalived
```

从节点：

```shell
[root@59-139 ~]# docker run -d --net=host --cap-add NET_ADMIN \
 -e KEEPALIVED_AUTOCONF=true                  \
 -e KEEPALIVED_STATE=BACKUP                   \
 -e KEEPALIVED_INTERFACE=ens33                 \
 -e KEEPALIVED_VIRTUAL_ROUTER_ID=2            \
 -e KEEPALIVED_UNICAST_SRC_IP=192.168.59.140  \
 -e KEEPALIVED_UNICAST_PEER_0=192.168.59.139  \
 -e KEEPALIVED_TRACK_INTERFACE_1=ens33         \
 -e KEEPALIVED_VIRTUAL_IPADDRESS_1="192.168.59.100/24 dev ens33" \
 arcts/keepalived
```

***

参考链接：<https://hub.docker.com/r/arcts/keepalived>
