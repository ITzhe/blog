---
title: "Glusterfs分布式存储"
date: 2019-09-13T10:59:21+08:00
draft: false
tags: ["高可用","存储"]
---

#volume卷

分布式卷（distributed）文件通过hash算法随机分布到bricks组成的卷上

复制式卷（replicated）类似raid1，replica数必须等于volume中brick所包含的存储服务器数。

条带式卷（striped）类似raid0，strips数必须等于volume中brick所包含的存储服务器数，文件被分布成数据块，以round robin的方式存在bricks中，并发粒度是数据块，大文件性能好。

分布式条带卷（distributed striped）volume中brick所包含的存储服务器数必须是stripe的倍数（>=2倍），兼顾分布式和条带式的功能。

**分布式复制卷**（distributed replicated）volume中brick所包含的存储服务器数必须是stripe的倍数（>=2倍），兼顾分布式和复制卷的功能。

#分布式卷

加入存储池

	[root@mystorage1 ~]# gluster peer probe mystorage2
	peer probe: success. 
	[root@mystorage1 ~]# gluster peer probe mystorage3
	peer probe: success. 
	[root@mystorage1 ~]# gluster peer probe mystorage4
	peer probe: success. 

在其他节点检查

	[root@mystorage4 ~]# gluster peer status
	Number of Peers: 3
	
	Hostname: mystorage1
	Uuid: 429d3353-dbcc-47d7-b3b5-4c3267fa26df
	State: Peer in Cluster (Connected)

	Hostname: mystorage3
	Uuid: 7c14cd1f-e801-48ca-8f23-09b017537400
	State: Peer in Cluster (Connected)

	Hostname: mystorage2
	Uuid: 14b4575a-2ba3-496b-96ea-9a4fe60819b3
	State: Peer in Cluster (Connected)

初始化

	yum install xfsprogs -y
	mkfs.xfs -f /dev/sdb
	mkdir -p /storage/brick1
	mount /dev/sdb /storage/brick1/
	echo "/dev/sdb /storage/brick1/  xfs defaults 0 0" >> /etc/fstab 
	mount -a

创建卷（整合磁盘）

	[root@mystorage1 ~]# gluster volume create gv1 mystorage1:/storage/brick1/ mystorage2:/storage/brick1/ force 
	volume create: gv1: success: please start the volume to access data

启动卷

	[root@mystorage1 ~]# gluster volume start gv1
	volume start: gv1: success
	[root@mystorage4 ~]# gluster volume gv1 info

挂载卷

	[root@mystorage3 ~]# mount -t glusterfs 127.0.0.1:/gv1 /mnt/
	[root@mystorage3 ~]# df -h
	…………
	127.0.0.1:/gv1   20G   65M   20G   1% /mnt

把刚才1和2的卷整合在一起之后，共享出来，然后3挂在到gv1种

测试
	
	[root@mystorage4 ~]# mount -t glusterfs 127.0.0.1:/gv1 /mnt/
	[root@mystorage4 ~]# mv d4 /mnt/
	[root@mystorage1 ~]# mount -t glusterfs 127.0.0.1:/gv1 /mnt/
	[root@mystorage1 ~]# ls /mnt/
	d4

#分布式复制卷

	[root@mystorage2 ~]# gluster volume create gv2 replica 2 mystorage3:/storage/brick1/ mystorage4:/storage/brick1/ force 
	volume create: gv2: success: please start the volume to access data

	[root@mystorage2 ~]# gluster volume info gv2
 
	Volume Name: gv2
	Type: Replicate
	Volume ID: 42949fc2-4400-4637-84c7-28aafed7676e
	Status: Created
	Number of Bricks: 1 x 2 = 2
	Transport-type: tcp
	Bricks:
	Brick1: mystorage3:/storage/brick1
	Brick2: mystorage4:/storage/brick1
	Options Reconfigured:
	performance.readdir-ahead: on
	[root@mystorage1 ~]# gluster volume restart gv2
	volume start: gv2: success
	[root@mystorage1 ~]# df -h
	…… ………
	127.0.0.1:/gv1   20G   65M   20G   1% /mnt
	127.0.0.1:/gv2   10G   33M   10G   1% /opt

总结：分布巻就像RAID0一样，是一份数据写在了两个地方，把一个数据打散了；而复制卷就像RAID1一样，把一份数据写在了多份。

	mkfs.xfs -f /dev/sdc
	mkdir -p /storage/brick2
	mount /dev/sdc /storage/brick2
	echo "/dev/sdc /storage/brick2/  xfs defaults 0 0" >> /etc/fstab 
	df -h
	#gluster volume create gv3 stripe 2 mystorage3:/storage/brick2/ mystorage4:/storage/brick2 force
	gluster volume start gv3
	mkdir /gv1 /gv2 /gv3

	[root@mystorage4 ~]# mount -t glusterfs 127.0.0.1:gv1 /gv1
	[root@mystorage4 ~]# mount -t glusterfs 127.0.0.1:gv2 /gv2
	[root@mystorage4 ~]# mount -t glusterfs 127.0.0.1:gv3 /gv3
	[root@mystorage4 ~]# dd if=/dev/zero bs=1024 count=10000 of=/gv3/10M.file
	[root@mystorage4 ~]# dd if=/dev/zero bs=1024 count=20000 of=/gv3/20M.file
	[root@mystorage4 gv3]# ll -h
	total 30M
	-rw-r--r--. 1 root root 9.8M Dec 27 12:19 10M.file
	-rw-r--r--. 1 root root  20M Dec 27 12:19 20M.file
	[root@mystorage4 gv3]# ll /storage/brick2/ -h
	total 15M
	-rw-r--r--. 2 root root 4.9M Dec 27 12:19 10M.file
	-rw-r--r--. 2 root root 9.8M Dec 27 12:19 20M.file

注意看大小

	[root@mystorage3 ~]# mkdir /gv1 /gv2 /gv3
	[root@mystorage3 ~]# mount -t glusterfs 127.0.0.1:gv3 /gv3

	[root@mystorage3 ~]# ll /gv3/
	total 30000
	-rw-r--r--. 1 root root 10240000 Dec 27 12:19 10M.file
	-rw-r--r--. 1 root root 20480000 Dec 27 12:19 20M.file
	[root@mystorage3 ~]# ll /storage/brick2/
	total 15032
	-rw-r--r--. 2 root root  5128192 Dec 27 12:19 10M.file
	-rw-r--r--. 2 root root 10256384 Dec 27 12:19 20M.file

注意看大小

#增加/删除磁盘

	[root@mystorage3 ~]# gluster volume stop gv2
	Stopping volume will make its data inaccessible. Do you want to continue? (y/n) y
	volume stop: gv2: success
	[root@mystorage3 ~]# gluster volume add-brick gv2 replica 2 mystorage1:/storage/brick2/ mystorage2:/storage/brick2 force
	volume add-brick: success
	[root@mystorage3 ~]# gluster volume start gv2
	volume start: gv2: success
	[root@mystorage4 gv3]# umount /gv2
	[root@mystorage4 gv3]# mount -t glusterfs 127.0.0.1:gv2 /gv2

扩容之后还需要磁盘平衡，否则是无法再新加入的磁盘中写入数据的

	[root@mystorage4 gv2]# gluster volume rebalance gv2 start	
	[root@mystorage4 gv2]# gluster volume rebalance gv2 status
	
注意：增加的brick必须是存储节点的倍数，例如reolica为2，你增加的数量必须是2 4 6 8 ……

	gluster volume stop gv2
	gluster volume remove-brick gv2 replica 2 mystorage1:/storage/brick2/ mystorage2:/storage/brick2 force

#删除卷
	umoun gv1
	gluster volume stop gv1
	gluster volume delete gv1

	




