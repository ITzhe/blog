---
title: "Linux System Tuning"
date: 2016-03-02T20:49:41+08:00
draft: false
slug: "linux-system-tuning"
tags: ["Tuning"]
---

# System tuning

1. Trim startup services to the minimum.

2. Disable remote root login, change the SSH port, switch remote login to key-based authentication, and use a VPN internal connection if necessary.

3. Disable iptables and SELinux as the workload requires.

4. Switch to a faster domestic YUM mirror.

5. Set the file character set — UTF-8 is best.

7. Customize the login banner in `/etc/issue`.

8. Synchronize the time.

9. Set a connection timeout for terminals.

10. Avoid IP addresses — prefer hostnames.

11. File locking (use with caution).

6. Adjust the file descriptor limit:

	vim /etc/security/limits.conf

	* soft nofile 65535
	* hard nofile 65535 

# Kernel tuning

Enable kernel forwarding:

	net.ipv4.ip_forward = 1

Set the timewait limit (default 180000):

	net.ipve.tcp_max_tw_buckets = 6000

Sets the range of ports the system is allowed to open:

	net.ipv4.ip_local_port_range = 1024 65000

Enable fast TIME_WAIT recycling:

	net.ipv4.tcp_tw_recycle = 1

Enable reuse, allowing TIME-WAIT sockets to be reused for new TCP connections:

	net.ipv4.tcp_tw_reuse = 1

Enable SYN cookies, which handle the SYN queue when it overflows:

	net.ipv4.tcp_syncookies = 1

Tunes how many TCP connections the system initiates at once. Under high concurrency the default can cause connection timeouts or retransmissions, so this needs to be tuned against the expected concurrency. The default is 128:

	net.core.somaxconn = 262144

The maximum number of packets queued when each network interface receives packets faster than the kernel can process them:

	net.core.netdev_max_backlog = 262144

Sets how many TCP sockets may be left unattached to any user file handle. Beyond this number, orphaned connections are reset immediately and a warning is logged. This limit exists only to guard against simple DoS attacks — do not rely on it too heavily or reduce it deliberately; in most cases it should be increased:

	net.ipv4.tcp_max_orphans = 262144

The maximum number of connection requests that have not yet received an acknowledgement from the client. For a system with 128MB of memory the default is 1024; for small-memory systems it is 128:

	net.ipv4.tcp_max_syn_backlog = 262144

The number of SYN+ACK packets sent before the kernel gives up on a connection:

	net.ipv4.tcp_synack_retries = 1

The number of SYN packets sent before the kernel gives up establishing a connection:

	net.ipv4.tcp_syn_retries = 1

How long a socket stays in FIN-WAIT-2. The default is 60 seconds:

	net.ipv4.tcp_fin_timeout = 1

How often TCP sends keepalive messages on a long connection. The default is 2 hours:

	net.ipv4.tcp_keepalive_time = 30

Tunes the swap usage threshold as a percentage. (100-10) = 90 means swap is used once memory usage reaches 90%. For Redis servers, 0 is recommended:

	/proc/sys/vm/swappiness 
	10

This article is short and will be expanded over time — suggestions are welcome.
