---
title: "Installing Keepalived with Docker"
date: 2023-03-13T17:44:11+08:00
draft: false
slug: "docker-keepalived"
tags: ["Quick Deploy", "docker"]
---

Master node:

```shell
[root@59-139 ~]# docker run -d --net=host --cap-add NET_ADMIN \
 -e KEEPALIVED_AUTOCONF=true                  \
 # role \
 -e KEEPALIVED_STATE=MASTER                   \
 # network interface to bind \
 -e KEEPALIVED_INTERFACE=ens33                 \
 # keepalived communication ID \
 -e KEEPALIVED_VIRTUAL_ROUTER_ID=2            \
 # unicast source address \
 -e KEEPALIVED_UNICAST_SRC_IP=192.168.59.139  \
 -e KEEPALIVED_UNICAST_PEER_0=192.168.59.140  \
 # interface to track \
 -e KEEPALIVED_TRACK_INTERFACE_1=ens33         \
 # virtual VIP \
 -e KEEPALIVED_VIRTUAL_IPADDRESS_1="192.168.59.100/24 dev ens33" \
 arcts/keepalived
```

Backup node:

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

Reference: <https://hub.docker.com/r/arcts/keepalived>
