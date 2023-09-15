---
title: "KVM虚拟机"
date: 2016-05-02T17:44:11+08:00
draft: false
tags: ["KVM"] 
---
最近闲着无聊，对比了docker和KVM，发现docker很厉害啊，未来的成长空间非常不错，但是目前还是有些不足，比如一些对于隔离的效果不是很好，再等两年成熟之后再去研究，现在感觉还是KVM比较实用，玩了玩整理了份文档，供大家分享：

###基础环境
	[root@localhost ~]# cat /etc/redhat-release 
	CentOS Linux release 7.1.1503 (Core) 
	[root@localhost ~]# uname -r
	3.10.0-229.el7.x86_64

###查看是否支持
	
	grep -E '(vmx|svm)' /proc/cpuinfo
	
###安装

	yum install qemu-kvm libvirt libvirt-python libguestfs-tools virt-install qemu-kvm-toools virt-manager

###启动

	systemctl start libvirtd
	systemctl status libvirtd

###创建虚拟机

	qemu-img create -f raw Centos-7.raw 10G		#在当前目录创建一个格式为raw的空的虚拟机，大小为10G

	virt-install --name Centos-7 --ram 1024 --vcpus=1 --disk path=Centos-7.raw --cdrom=CentOS-7-x86_64-DVD-1503-01_2.iso  --graphics vnc,listen=0.0.0.0 

使用VNC工具连接到主机即可（安装操作系统这里不再介绍）

查看运行中的虚拟机

	virsh list --all

	 Id    Name                           State
	----------------------------------------------------
	 7     Centos-7                       running


查看虚拟机的详细信息

	[root@localhost media]# virsh dominfo  Centos-7
	Id:             7
	Name:           Centos-7
	UUID:           544cdb00-6c2c-4c93-9e11-086920b89320
	OS Type:        hvm
	State:          running
	CPU(s):         1
	CPU time:       46.9s
	Max memory:     1048576 KiB
	Used memory:    1048576 KiB
	Persistent:     yes
	Autostart:      disable
	Managed save:   no
	Security model: none
	Security DOI:   0	

##KVM的扩容与缩容

####内存

	virsh setmem Centos-7 512M

####硬盘

硬盘也可以动态扩容、缩容，但是笔者经验不建议，可能丢失数据，如果数据硬盘不够了，再重新添加一块硬盘。

##格式转换

	[root@linux-node2 opt]# qemu-img convert -f raw -O qcow2 Centos-7.raw Centos-7.qcow2

	[root@linux-node2 opt]# ll -h Centos-7.*
	-rw-r--r-- 1 root root 1017M May  4 16:18 Centos-7.qcow2
	-rw-r--r-- 1 qemu qemu   10G May  4 16:11 Centos-7.raw

#RAW与QCOW2优缺点：

	raw格式是最原始的一种格式，特点是I/O性能最好的一种格式，没有之一，缺点就是功能很少，有很多快照、加密、压缩都不支持，而且特别大，最开始制定10G就占用10G的空间。
	qcow2与raw相反，功能很多，支持快照、加密、压缩，而且占用资源小，在原始的镜像上面只保留修改的部分，但是性能差于raw。


##让虚拟机桥接到物理网卡

此时的虚拟机还不能上网，仅仅是运行了一个系统，要想上网进行如下操作：

	brctl addbr br0

模拟出一块网卡名字为 br0

	brctl addif br0 eth0

桥接到eth0，注意，这样会离开断开与服务器的连接，因为服务器的eth0是没有IP地址的

	 ip addr del dev eth0 192.168.56.11/24

删除原eth0的IP地址

	ifconfig br0 192.168.56.11/24 up

此时虽然连上了服务器，但是任然不能上网，因为路由不对，添加以下：

	route add default gw 1.1.1.1（网关地址）

现在会断开与KVM虚拟机的连接，没关系，修改虚拟机的XML文件：

	virsh edit Centos-7		#修改为以下两行

	     <interface type='bridge'>
	       <source bridge='br0'/>

重启一下

	virsh  reboot Centos-7

然后配置IP地址、网关、DNS等即可连接上网，此处不再演示

----
----
----

附带一些常用命令：

开机：

	virsh start test1

关机：

	virsh shutdown test1

强制关机：

	virsh destroy test1

重新启动：

	virsh reboot test1

通过配置文档启动主机：

	virsh create /etc/libvirt/qemu/test1.xml

查看主机状态：

	virsh list --all

停止/挂机虚拟机：

	virsh suspend test1

保存虚拟机：

	virsh save test1  
 	或者
	virsh dumpxml Centos-7 > dump_kvm.xml

还原虚拟机：

	virsh resume test1

---

#快照功能

默认快照文件放在 /var/lib/libvirt/qemu/snapshot/

拍摄快照：

	virsh snapshot-create test1

查看快照：

	virsh snapshot-list test1

		 Name                 Creation Time             State
	------------------------------------------------------------
	 1486394873           2017-02-06 23:27:53 +0800 shutoff				#上次快照
	 1486394993           2017-02-06 23:29:53 +0800 shutoff				#这次快照

恢复快照：

	virsh snapshot-revert test1 1486394873
	
---
---

例1：修改CPU数量

	virsh edit Centos-7

	<vcpu placement='auto' current='1'>4</vcpu>						#CPU上限是4个，目前是一个

	virsh setvcpus Centos-7 2 --live								#也可以使用--config参数
	virsh reboot  Centos-7											#重启可选


例2：添加硬盘

	qemu-img create -f qcow2 add.img 20G

	virsh attach-disk Centos-7 /opt/add.img sdb					#添加一块硬盘（热添加，重启失效）

	virsh edit Centos-7											#写入配置文件
		…………
	    </disk>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='none'/>
      <source file='/opt/add.img'/>
      <target dev='sdb' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x06' function='0x0'/>
    </disk>

	virsh reboot Centos-7

后来我有找到更简单的一种方法：

	virsh attach-disk Centos-7 /opt/add.img sdb --config