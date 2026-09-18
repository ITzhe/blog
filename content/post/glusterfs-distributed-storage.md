---
title: "GlusterFS Distributed Storage"
date: 2019-09-13T10:59:21+08:00
draft: false
slug: "glusterfs-distributed-storage"
tags: ["High Availability", "Storage"]
---

# Volume types

**Distributed** — files are spread randomly across the bricks that make up the volume using a hash algorithm.

**Replicated** — similar to RAID1; the replica count must equal the number of storage servers contained in the volume's bricks.

**Striped** — similar to RAID0; the stripe count must equal the number of storage servers in the volume's bricks. Files are split into data blocks that live on the bricks in round-robin fashion. Concurrency is at the block level, so large files perform well.

**Distributed striped** — the number of storage servers in the volume's bricks must be a multiple of the stripe count (>= 2x). Combines the features of distributed and striped volumes.

**Distributed replicated** — the number of storage servers in the volume's bricks must be a multiple of the replica count (>= 2x). Combines the features of distributed and replicated volumes.

# Distributed volume

Add the nodes to the storage pool:

	[root@mystorage1 ~]# gluster peer probe mystorage2
	peer probe: success. 
	[root@mystorage1 ~]# gluster peer probe mystorage3
	peer probe: success. 
	[root@mystorage1 ~]# gluster peer probe mystorage4
	peer probe: success. 

Check from another node:

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

Initialize the disks:

	yum install xfsprogs -y
	mkfs.xfs -f /dev/sdb
	mkdir -p /storage/brick1
	mount /dev/sdb /storage/brick1/
	echo "/dev/sdb /storage/brick1/  xfs defaults 0 0" >> /etc/fstab 
	mount -a

Create the volume (pooling the disks):

	[root@mystorage1 ~]# gluster volume create gv1 mystorage1:/storage/brick1/ mystorage2:/storage/brick1/ force 
	volume create: gv1: success: please start the volume to access data

Start the volume:

	[root@mystorage1 ~]# gluster volume start gv1
	volume start: gv1: success
	[root@mystorage4 ~]# gluster volume gv1 info

Mount the volume:

	[root@mystorage3 ~]# mount -t glusterfs 127.0.0.1:/gv1 /mnt/
	[root@mystorage3 ~]# df -h
	…………
	127.0.0.1:/gv1   20G   65M   20G   1% /mnt

After pooling the volumes from nodes 1 and 2, share it and mount it as `gv1` on node 3.

Test:

	[root@mystorage4 ~]# mount -t glusterfs 127.0.0.1:/gv1 /mnt/
	[root@mystorage4 ~]# mv d4 /mnt/
	[root@mystorage1 ~]# mount -t glusterfs 127.0.0.1:/gv1 /mnt/
	[root@mystorage1 ~]# ls /mnt/
	d4

# Distributed replicated volume

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

Summary: a distributed volume is like RAID0 — it writes a single copy of the data but splits it across places. A replicated volume is like RAID1 — it writes the data out in multiple copies.

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

Note the file sizes.

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

Note the file sizes.

# Adding / removing disks

	[root@mystorage3 ~]# gluster volume stop gv2
	Stopping volume will make its data inaccessible. Do you want to continue? (y/n) y
	volume stop: gv2: success
	[root@mystorage3 ~]# gluster volume add-brick gv2 replica 2 mystorage1:/storage/brick2/ mystorage2:/storage/brick2 force
	volume add-brick: success
	[root@mystorage3 ~]# gluster volume start gv2
	volume start: gv2: success
	[root@mystorage4 gv3]# umount /gv2
	[root@mystorage4 gv3]# mount -t glusterfs 127.0.0.1:gv2 /gv2

After expanding you still need to rebalance the disks, otherwise no data can be written to the newly added disks.

	[root@mystorage4 gv2]# gluster volume rebalance gv2 start	
	[root@mystorage4 gv2]# gluster volume rebalance gv2 status
	
Note: the number of bricks added must be a multiple of the replica count. For example, with a replica count of 2 you must add 2, 4, 6, 8, ... bricks.

	gluster volume stop gv2
	gluster volume remove-brick gv2 replica 2 mystorage1:/storage/brick2/ mystorage2:/storage/brick2 force

# Deleting a volume

	umoun gv1
	gluster volume stop gv1
	gluster volume delete gv1
