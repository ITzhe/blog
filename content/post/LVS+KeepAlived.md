---
title: "LVS+KeepAlived"
date: 2017-09-13T10:59:21+08:00
draft: false
tags: ["高可用"]
---

最近闲着无聊复习了一下高可用Keepalive和LVS反向代理，觉的挺经典的，整理了一篇文档

在部署之前，我们先对LVS的一些基础知识了解一下

#LVS的模式

###NAT模式
 
NAT用法本来是因为网络IP地址不足而把内部保留IP地址通过映射转换成公网地址的一种上网方式(原地址NAT)｡如果把NAT的过程稍微变化,就可以成为负载均衡的一种方式｡原理其实就是把从客户端发来的IP包的IP头目的地址在DR上换成其中一台REALSERVER的IP地址并发至此REALSERVER,而REALSERVER则在处理完成后把数据经过DR主机发回给客户端,DR在这个时候再把数据包的原IP地址改为DR接口上的IP地址即可｡期间,无论是进来的流量,还是出去的流量,都必须经过DR｡

![](http://i.imgur.com/73k03Pw.png)

###FULLNAT 模式

![](http://i.imgur.com/thRxIAJ.png)
 
###TUNNEL模式
 
隧道模式则类似于VPN的方式,使用网络分层的原理,在从客户端发来的数据包的基础上,封装一个新的IP头标记(不完整的IP头,只有目的IP部)发给REALSERVER,REALSERVER收到后,先把DR发过来的数据包的头给解开,还原其数据包原样,处理后,直接返回给客户端,而不需要再经过DR｡需要注意的是,由于REALSERVER需要对DR发过来的数据包进行还原,也就是说必须支持IPTUNNEL协议｡所以,在REALSERVER的内核中,必须编译支持IPTUNNEL这个选项｡IPTUNNEL也在Net working options里面｡
 
![](http://i.imgur.com/1f4ydpR.png)

###DR模式
 
直接路由模式比较特别,很难说和什么方面相似,前2种模式基本上都是工作在网络层上(三层),而直接路由模式则应该是工作在数据链路层上(二层)｡其原理为,DR和REALSERVER都使用同一个IP对外服务｡但只有DR对ARP请求进行响应,所有REALSERVER对本身这个IP的ARP请求保持静默｡也就是说,网关会把对这个服务IP的请求全部定向给DR,而DR收到数据包后根据调度算法,找出对应的REALSERVER,把目的MAC地址改为REALSERVER的MAC并发给这台REALSERVER｡这时REALSERVER收到这个数据包,则等于直接从客户端收到这个数据包无异,处理后直接返回给客户端｡由于DR要对二层包头进行改换,所以DR和REALSERVER之间必须在一个广播域,也可以简单的理解为在同一台交换机上｡

![](http://i.imgur.com/qZlKfnd.png)

#LVS的算法

###轮叫调度(Round-RobinScheduling)
 
调度器通过"轮叫"调度算法将外部请求按顺序轮流分配到集群中的真实服务器上,它均等地对待每一台服务器,而不管服务器上实际的连接数和系统负载｡
 
###加权轮叫调度(WeightedRound-RobinScheduling)
 
调度器通过"加权轮叫"调度算法根据真实服务器的不同处理能力来调度访问请求｡这样可以保证处理能力强的服务器处理更多的访问流量｡调度器可以自动问询真实服务器的负载情况,并动态地调整其权值｡
 
###最小连接调度(Least-ConnectionScheduling)
 
调度器通过"最少连接"调度算法动态地将网络请求调度到已建立的链接数最少的服务器上｡如果集群系统的真实服务器具有相近的系统性能,采用"最小连接"调度算法可以较好地均衡负载｡
 
###加权最小连接调度(WeightedLeast-ConnectionScheduling)
 
在集群系统中的服务器性能差异较大的情况下,调度器采用"加权最少链接"调度算法优化负载均衡性能,具有较高权值的服务器将承受较大比例的活动连接负载｡调度器可以自动问询真实服务器的负载情况,并动态地调整其权值
 
###基于局部性的最少链接(Locality-BasedLeastConnectionsScheduling)
 
基于局部性的最少链接"调度算法是针对目标IP地址的负载均衡,目前主要用于Cache集群系统｡该算法根据请求的目标IP地址找出该目标IP地址最近使用的服务器,若该服务器是可用的且没有超载,将请求发送到该服务器;若服务器不存在,或者该服务器超载且有服务器处于一半的工作负载,则用"最少链接"的原则选出一个可用的服务器,将请求发送到该服务器｡
 
###带复制的基于局部性最少链接(Locality-BasedLeastConnectionswithReplicationScheduling)
 
带复制的基于局部性最少链接"调度算法也是针对目标IP地址的负载均衡,目前主要用于Cache集群系统｡它与LBLC算法的不同之处是它要维护从一个目标IP地址到一组服务器的映射,而LBLC算法维护从一个目标IP地址到一台服务器的映射｡该算法根据请求的目标IP地址找出该目标IP地址对应的服务器组,按"最小连接"原则从服务器组中选出一台服务器,若服务器没有超载,将请求发送到该服务器,若服务器超载;则按"最小连接"原则从这个集群中选出一台服务器,将该服务器加入到服务器组中,将请求发送到该服务器｡同时,当该服务器组有一段时间没有被修改,将最忙的服务器从服务器组中删除,以降低复制的程度
 
###目标地址散列调度(DestinationHashingScheduling)
 
目标地址散列"调度算法根据请求的目标IP地址,作为散列键(HashKey)从静态分配的散列表找出对应的服务器,若该服务器是可用的且未超载,将请求发送到该服务器,否则返回空
 
###源地址散列调度(SourceHashingScheduling)
 
源地址散列"调度算法根据请求的源IP地址,作为散列键(HashKey)从静态分配的散列表找出对应的服务器,若该服务器是可用的且未超载,将请求发送到该服务器,否则返回空｡



	yum install keepalived ipvsadm

#keepalive高可用

vim /etc/keepalived/keepalived.conf 
	
	! Configuration File for keepalived

	global_defs {
	   notification_email {
	     acassen@firewall.loc
	     failover@firewall.loc
	     sysadmin@firewall.loc
	   }
	   notification_email_from Alexandre.Cassen@firewall.loc
	   smtp_server 127.0.0.1
	   smtp_connect_timeout 30
	   router_id LVS-BACKUP
	}

	vrrp_instance VI_1 {					#实例的ID
    	state BACKUP						#主节点为MASTER
    	interface eth0
    	virtual_router_id 51				# ID一定要统一两边
    	priority 50							# 备节点一定要低于主节点
    	advert_int 1
    	authentication {		
    	    auth_type PASS
    	    auth_pass 1111
    	}
    	virtual_ipaddress {					
    	    192.168.56.250					#VIP的地址
    	}
	}	

主节点和主要是把角色和优先级调整一下即可，这里不再重复

#keepalive+LVS高可用负载均衡

还是在keepalive的配置文件末尾加入以下：

		virtual_server 192.168.56.250 80 {				VIP的地址
	    delay_loop 6
	    lb_algo rr										#LVS的算法（这里采用DR模式）	
	    lb_kind DR
	    nat_mask 255.255.255.0
	    persistence_timeout 50
	    protocol TCP
	
	    real_server 192.168.56.11 80 {					#后端的节点IP地址
	        weight 1
	        TCP_CHECK {									# 健康检查功能
	            connect_timeout 3
	            nb_get_retry 3
				delay_before_retry 3
	            connect_port 80
	        }
	    }

	    real_server 192.168.56.12 80 {
	        weight 1
	        TCP_CHECK {
	            connect_timeout 3
	            nb_get_retry 3
	            delay_before_retry 3
	            connect_port 80
	        }
	    }
	}

在每个客户端的节点加入ARP的抑制

	ifconfig  lo:0 192.168.56.250/32 up
	route add -host 192.168.56.250 dev lo
	echo "1" >/proc/sys/net/ipv4/conf/lo/arp_ignore 
	echo "2" >/proc/sys/net/ipv4/conf/lo/arp_announce 
	echo "1" >/proc/sys/net/ipv4/conf/all/arp_ignore 
	echo "2" >/proc/sys/net/ipv4/conf/all/arp_announce 



