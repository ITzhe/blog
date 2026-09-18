---
title: "KVM Virtual Machines"
date: 2016-05-02T17:44:11+08:00
draft: false
slug: "kvm-virtual-machines"
tags: ["KVM"]
---

Recently I had some spare time and compared Docker with KVM. Docker is impressive and has a lot of room to grow, but it still falls short in a few areas — for example, isolation is not great. I will revisit it in a couple of years once it has matured. For now KVM feels more practical. Here is a write-up I put together from playing around with it, shared for anyone interested:

### Base environment

	[root@localhost ~]# cat /etc/redhat-release 
	CentOS Linux release 7.1.1503 (Core) 
	[root@localhost ~]# uname -r
	3.10.0-229.el7.x86_64

### Check whether virtualization is supported

	
	grep -E '(vmx|svm)' /proc/cpuinfo
	
### Install

	yum install qemu-kvm libvirt libvirt-python libguestfs-tools virt-install qemu-kvm-toools virt-manager

### Start

	systemctl start libvirtd
	systemctl status libvirtd

### Create a virtual machine

	qemu-img create -f raw Centos-7.raw 10G		# create an empty 10G raw disk in the current directory

	virt-install --name Centos-7 --ram 1024 --vcpus=1 --disk path=Centos-7.raw --cdrom=CentOS-7-x86_64-DVD-1503-01_2.iso  --graphics vnc,listen=0.0.0.0 

Then connect to the host with a VNC client (installing the OS is out of scope here).

List the running virtual machines:

	virsh list --all

	 Id    Name                           State
	----------------------------------------------------
	 7     Centos-7                       running


Show detailed information about a virtual machine:

	[root@localhost media]# virsh dominfo  Centos-7
	Id:             7
	Name:           Centos-7
	UUID:          544cdb00-6c2c-4c93-9e11-086920b89320
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

## Scaling KVM up and down

#### Memory

	virsh setmem Centos-7 512M

#### Disk

Disks can also be resized dynamically, but in my experience this is not advisable — you can lose data. If a disk runs out of space, just add another disk instead.

## Format conversion

	[root@linux-node2 opt]# qemu-img convert -f raw -O qcow2 Centos-7.raw Centos-7.qcow2

	[root@linux-node2 opt]# ll -h Centos-7.*
	-rw-r--r-- 1 root root 1017M May  4 16:18 Centos-7.qcow2
	-rw-r--r-- 1 qemu qemu   10G May  4 16:11 Centos-7.raw

# Pros and cons of RAW vs QCOW2

	raw is the most primitive format and has the best I/O performance, bar none.
	Its downside is a very limited feature set: snapshots, encryption, and
	compression are all unsupported, and it is huge — allocating 10G really
	does consume 10G from the start.
	qcow2 is the opposite: feature-rich, supporting snapshots, encryption, and
	compression, and it uses space efficiently by storing only the changes on
	top of the base image — but performance is worse than raw.


## Bridging the virtual machine to a physical NIC

At this point the virtual machine still has no network access — it is just running a system. To get it online:

	brctl addbr br0

Create a virtual bridge interface named `br0`:

	brctl addif br0 eth0

Bridge it to `eth0`. Be careful: this will drop your connection to the server, because the server's `eth0` has no IP address.

	 ip addr del dev eth0 192.168.56.11/24

Remove the original IP address from `eth0`:

	ifconfig br0 192.168.56.11/24 up

You can now reach the server again, but networking still will not work because the route is wrong. Add:

	route add default gw 1.1.1.1（gateway address）

This will disconnect you from the KVM virtual machine — that is fine. Edit the virtual machine's XML file:

	virsh edit Centos-7		# change it to the following two lines

	     <interface type='bridge'>
	       <source bridge='br0'/>

Reboot:

	virsh  reboot Centos-7

Then configure the IP address, gateway, DNS, and so on, and it will be online. I will not demonstrate that here.

----
----
----

A few commonly used commands:

Power on:

	virsh start test1

Power off:

	virsh shutdown test1

Force power off:

	virsh destroy test1

Reboot:

	virsh reboot test1

Start a domain from a config file:

	virsh create /etc/libvirt/qemu/test1.xml

Check domain status:

	virsh list --all

Suspend a virtual machine:

	virsh suspend test1

Save a virtual machine:

	virsh save test1  
 	or
	virsh dumpxml Centos-7 > dump_kvm.xml

Restore a virtual machine:

	virsh resume test1

---

# Snapshots

Snapshot files are stored in `/var/lib/libvirt/qemu/snapshot/` by default.

Take a snapshot:

	virsh snapshot-create test1

List snapshots:

	virsh snapshot-list test1

		 Name                 Creation Time             State
	------------------------------------------------------------
	 1486394873           2017-02-06 23:27:53 +0800 shutoff				#previous snapshot
	 1486394993           2017-02-06 23:29:53 +0800 shutoff				#this snapshot

Restore a snapshot:

	virsh snapshot-revert test1 1486394873
	
---
---

Example 1: changing the CPU count

	virsh edit Centos-7

	<vcpu placement='auto' current='1'>4</vcpu>						#max 4 CPUs, currently 1

	virsh setvcpus Centos-7 2 --live								#you can also use --config
	virsh reboot  Centos-7											#restart optional


Example 2: adding a disk

	qemu-img create -f qcow2 add.img 20G

	virsh attach-disk Centos-7 /opt/add.img sdb					#hot-add a disk (lost on reboot)

	virsh edit Centos-7											#write it into the config file
		…………
	    </disk>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='none'/>
      <source file='/opt/add.img'/>
      <target dev='sdb' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x06' function='0x0'/>
    </disk>

	virsh reboot Centos-7

Later I found a simpler approach:

	virsh attach-disk Centos-7 /opt/add.img sdb --config
