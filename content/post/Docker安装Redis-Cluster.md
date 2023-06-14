---
title: "Docker安装Redis Cluster"
date: 2023-06-14T14:29:17+08:00
draft: false
tags: ["docker"]
---


Redis 5.0.7

创建集群目录

    mkdir /home/redis-cluster

``` bash
port ${PORT}
protected-mode no
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
cluster-announce-ip 192.168.21.28 //自己服务器IP
cluster-announce-port ${PORT}
cluster-announce-bus-port 1${PORT}
appendonly yes
```

创建专有网络（可选）

    docker network create redis-net

创建conf和data目录

```bash
for port in `seq 7000 7005`; do \
  mkdir -p ./${port}/conf \
  && PORT=${port} envsubst < ./redis-cluster.tmpl > ./${port}/conf/redis.conf \
  && mkdir -p ./${port}/data; \
done
```

创建Redis容器

``` bash
for port in `seq 7000 7005`; do \
  docker run -d -ti -p ${port}:${port} -p 1${port}:1${port} \
  -v /home/redis-cluster/${port}/conf/redis.conf:/usr/local/etc/redis/redis.conf \
  -v /home/redis-cluster/${port}/data:/data \
  --restart always --name redis-${port} --net redis-net \
  --sysctl net.core.somaxconn=1024 redis redis-server /usr/local/etc/redis/redis.conf; \
done
```

随意进入一个容器

    docker exec -it e61133e98d01 /bin/bash

创建集群

    redis-cli --cluster create 192.168.21.28:7000 192.168.21.28:7001 192.168.21.28:7002 192.168.21.28:7002 192.168.21.28:7003 192.168.21.28:7004 192.168.21.28:7005 --cluster-replicas 1

输出记录
    
``` txt
>>> Performing hash slots allocation on 7 nodes...
Master[0] -> Slots 0 - 5460
Master[1] -> Slots 5461 - 10922
Master[2] -> Slots 10923 - 16383
Adding replica 192.168.21.28:7003 to 192.168.21.28:7000
Adding replica 192.168.21.28:7004 to 192.168.21.28:7001
Adding replica 192.168.21.28:7005 to 192.168.21.28:7002
Adding extra replicas...
Adding replica 192.168.21.28:7002 to 192.168.21.28:7000
>>> Trying to optimize slaves allocation for anti-affinity
[WARNING] Some slaves are in the same host as their master
M: d4b82300dfacedeaf7d50e0c3c06d9b7662603e1 192.168.21.28:7000
   slots:[0-5460] (5461 slots) master
M: f89d211a74b1e71b4b3aa12ae9491cd0657c9f06 192.168.21.28:7001
   slots:[5461-10922] (5462 slots) master
M: d02714dc30ed747bc23d8387684d0389b1552a61 192.168.21.28:7002
   slots:[10923-16383] (5461 slots) master
S: d02714dc30ed747bc23d8387684d0389b1552a61 192.168.21.28:7002
   replicates f89d211a74b1e71b4b3aa12ae9491cd0657c9f06
S: 5188757b51c2fc804ab9a09779cc83f3dd08e7e2 192.168.21.28:7003
   replicates d4b82300dfacedeaf7d50e0c3c06d9b7662603e1
S: 985e81724ea9b5664a19961f4a758689290856b2 192.168.21.28:7004
   replicates d02714dc30ed747bc23d8387684d0389b1552a61
S: 2f12b2eb90938cf2469bd6209f85dc42925e2129 192.168.21.28:7005
   replicates d4b82300dfacedeaf7d50e0c3c06d9b7662603e1
Can I set the above configuration? (type 'yes' to accept): yes
>>> Nodes configuration updated
>>> Assign a different config epoch to each node
>>> Sending CLUSTER MEET messages to join the cluster
Waiting for the cluster to join
....
>>> Performing Cluster Check (using node 192.168.21.28:7000)
M: d4b82300dfacedeaf7d50e0c3c06d9b7662603e1 192.168.21.28:7000
   slots:[0-5460] (5461 slots) master
   2 additional replica(s)
M: d02714dc30ed747bc23d8387684d0389b1552a61 192.168.21.28:7002
   slots:[10923-16383] (5461 slots) master
   1 additional replica(s)
S: 985e81724ea9b5664a19961f4a758689290856b2 192.168.21.28:7004
   slots: (0 slots) slave
   replicates d02714dc30ed747bc23d8387684d0389b1552a61
S: 2f12b2eb90938cf2469bd6209f85dc42925e2129 192.168.21.28:7005
   slots: (0 slots) slave
   replicates d4b82300dfacedeaf7d50e0c3c06d9b7662603e1
S: 5188757b51c2fc804ab9a09779cc83f3dd08e7e2 192.168.21.28:7003
   slots: (0 slots) slave
   replicates d4b82300dfacedeaf7d50e0c3c06d9b7662603e1
M: f89d211a74b1e71b4b3aa12ae9491cd0657c9f06 192.168.21.28:7001
   slots:[5461-10922] (5462 slots) master
[OK] All nodes agree about slots configuration.
>>> Check for open slots...
>>> Check slots coverage...
[OK] All 16384 slots covered.

```

连接测试
```bash
e61133e98d01        redis                                 "docker-entrypoint.s…"   25 minutes ago      Up 25 minutes       0.0.0.0:7005->7005/tcp, 6379/tcp, 0.0.0.0:17005->17005/tcp                                   redis-7005
4860f478463f        redis                                 "docker-entrypoint.s…"   25 minutes ago      Up 25 minutes       0.0.0.0:7004->7004/tcp, 6379/tcp, 0.0.0.0:17004->17004/tcp                                   redis-7004
16d6bb61118b        redis                                 "docker-entrypoint.s…"   25 minutes ago      Up 25 minutes       0.0.0.0:7003->7003/tcp, 6379/tcp, 0.0.0.0:17003->17003/tcp                                   redis-7003
7b6070c17724        redis                                 "docker-entrypoint.s…"   25 minutes ago      Up 25 minutes       0.0.0.0:7002->7002/tcp, 6379/tcp, 0.0.0.0:17002->17002/tcp                                   redis-7002
afd85937ac9a        redis                                 "docker-entrypoint.s…"   25 minutes ago      Up 25 minutes       0.0.0.0:7001->7001/tcp, 6379/tcp, 0.0.0.0:17001->17001/tcp                                   redis-7001
0298db107972        redis                                 "docker-entrypoint.s…"   25 minutes ago      Up 25 minutes       0.0.0.0:7000->7000/tcp, 6379/tcp, 0.0.0.0:17000->17000/tcp                                   redis-7000

redis-cli -c -h 192.168.21.28 -p 7002
192.168.21.28:7002> CLUSTER NODES
985e81724ea9b5664a19961f4a758689290856b2 192.168.21.28:7004@17004 slave d02714dc30ed747bc23d8387684d0389b1552a61 0 1576224546000 6 connected
2f12b2eb90938cf2469bd6209f85dc42925e2129 192.168.21.28:7005@17005 slave d4b82300dfacedeaf7d50e0c3c06d9b7662603e1 0 1576224547233 1 connected
5188757b51c2fc804ab9a09779cc83f3dd08e7e2 192.168.21.28:7003@17003 slave d4b82300dfacedeaf7d50e0c3c06d9b7662603e1 0 1576224546227 5 connected
f89d211a74b1e71b4b3aa12ae9491cd0657c9f06 192.168.21.28:7001@17001 master - 0 1576224546000 2 connected 5461-10922
d02714dc30ed747bc23d8387684d0389b1552a61 192.168.21.28:7002@17002 myself,master - 0 1576224544000 3 connected 10923-16383
d4b82300dfacedeaf7d50e0c3c06d9b7662603e1 192.168.21.28:7000@17000 master - 0 1576224547000 1 connected 0-5460
```

参考链接：

https://blog.csdn.net/tszxlzc/article/details/86565327

https://www.cnblogs.com/lianggp/articles/8136222.html