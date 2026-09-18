---
title: "LVS + Keepalived"
date: 2017-09-13T10:59:21+08:00
draft: false
slug: "lvs-keepalived"
tags: ["High Availability"]
---

I had some spare time recently and went back over high-availability Keepalived and LVS reverse proxying. It is a classic setup, so I put together a write-up.

Before deploying, let's go over some LVS fundamentals.

# LVS modes

### NAT mode

NAT was originally a way to get online when public IP addresses were scarce: private addresses were mapped through to a public address (source NAT). With a slight twist, this same process becomes a load-balancing method. The idea is that the DR (director) rewrites the destination address in the IP header of packets coming from the client to the IP of one of the real servers and forwards them there. The real server processes the request and sends the data back to the client through the DR, at which point the DR rewrites the source IP address to the IP on its own interface. In this mode, both inbound and outbound traffic must pass through the DR.

![](http://i.imgur.com/73k03Pw.png)

### FULLNAT mode

![](http://i.imgur.com/thRxIAJ.png)

### TUNNEL mode

Tunnel mode works like a VPN. Using network layering, it wraps a new IP header (an incomplete one, containing only the destination IP) around the packet from the client and sends it to the real server. When the real server receives it, it unwraps the header the DR added, restores the packet to its original form, processes it, and returns the result directly to the client without going back through the DR. Note that since the real server must restore the packet from the DR, it has to support the IPTUNNEL protocol — the IPTUNNEL option must be compiled into the real server's kernel. IPTUNNEL is also found under Networking options.

![](http://i.imgur.com/1f4ydpR.png)

### DR mode

Direct routing mode is unusual and hard to compare to anything else. The two modes above essentially operate at the network layer (layer 3), whereas direct routing operates at the data link layer (layer 2). The principle is that the DR and the real servers all serve the same IP to the outside world, but only the DR responds to ARP requests — all real servers stay silent about ARP requests for that IP. This means the gateway directs all requests for the service IP to the DR, and after receiving a packet the DR uses its scheduling algorithm to pick a real server, rewrites the destination MAC address to that server's MAC, and forwards it. The real server receives the packet and, as far as it can tell, it came straight from the client, so it processes it and replies directly. Because the DR has to rewrite layer-2 headers, the DR and the real servers must be in the same broadcast domain — in simple terms, on the same switch.

![](http://i.imgur.com/qZlKfnd.png)

# LVS scheduling algorithms

### Round-Robin Scheduling

The director distributes incoming requests to the real servers in the cluster in turn. It treats every server equally, regardless of the actual connection count or system load on each server.

### Weighted Round-Robin Scheduling

The director schedules requests according to the differing capacities of the real servers. Servers with more capacity handle a larger share of the traffic. The director can query the load on the real servers and adjust their weights dynamically.

### Least-Connection Scheduling

The director dynamically sends requests to the server with the fewest established connections. If the real servers in the cluster have similar performance, least-connection balances the load well.

### Weighted Least-Connection Scheduling

When server performance in the cluster varies widely, the director uses weighted least-connection to optimize load balancing. Servers with higher weights take a larger share of the active connection load. The director can query the real servers' load and adjust weights dynamically.

### Locality-Based Least Connections Scheduling

This algorithm balances load for a target IP address, and is mainly used in cache cluster systems. It finds the real server most recently used by the request's target IP. If that server is available and not overloaded, the request goes there. If it does not exist, or is overloaded while another server is at half load, then the least-connection principle picks an available server and the request is sent there.

### Locality-Based Least Connections with Replication Scheduling

This also balances load for a target IP address, again mainly for cache clusters. Unlike LBLC, it maintains a mapping from a target IP to a *group* of servers, whereas LBLC maps a target IP to a single server. The algorithm finds the server group for the request's target IP, picks a server from the group by least-connection, and sends the request there if that server is not overloaded. If it is overloaded, another server is selected by least-connection from the whole cluster, added to the group, and the request is sent to it. If the group has not been modified for a while, the busiest server is removed from it to reduce replication.

### Destination Hashing Scheduling

This algorithm uses the request's destination IP address as a hash key to find the corresponding server in a statically assigned hash table. If that server is available and not overloaded, the request goes there; otherwise it returns empty.

### Source Hashing Scheduling

This algorithm uses the request's source IP address as a hash key to find the corresponding server in a statically assigned hash table. If that server is available and not overloaded, the request goes there; otherwise it returns empty.



	yum install keepalived ipvsadm

# Keepalived high availability

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

	vrrp_instance VI_1 {					# instance ID
    	state BACKUP						# MASTER on the primary node
    	interface eth0
    	virtual_router_id 51				# must be identical on both sides
    	priority 50							# must be lower than the primary node's
    	advert_int 1
    	authentication {		
    	    auth_type PASS
    	    auth_pass 1111
    	}
    	virtual_ipaddress {					
    	    192.168.56.250					# the VIP address
    	}
	}	

For the primary node, just swap the role and the priority — I will not repeat it here.

# Keepalived + LVS high-availability load balancing

Append the following to the end of the keepalived config file:

		virtual_server 192.168.56.250 80 {				the VIP address
	    delay_loop 6
	    lb_algo rr										# LVS algorithm (DR mode here)
	    lb_kind DR
	    nat_mask 255.255.255.0
	    persistence_timeout 50
	    protocol TCP
	
	    real_server 192.168.56.11 80 {					# backend node IP
	        weight 1
	        TCP_CHECK {									# health check
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

Add ARP suppression on each backend node:

	ifconfig  lo:0 192.168.56.250/32 up
	route add -host 192.168.56.250 dev lo
	echo "1" >/proc/sys/net/ipv4/conf/lo/arp_ignore 
	echo "2" >/proc/sys/net/ipv4/conf/lo/arp_announce 
	echo "1" >/proc/sys/net/ipv4/conf/all/arp_ignore 
	echo "2" >/proc/sys/net/ipv4/conf/all/arp_announce 
