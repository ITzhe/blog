---
title: "Redis优化"
date: 2023-03-02T20:52:54+08:00
draft: false
tags: ["调优"]
---

# Redis 持久化方式

Redis 提供了多种不同级别的持久化方式：

	RDB 持久化可以在指定的时间间隔内生成数据集的时间点快照（point-in-time snapshot）。
	
	AOF AOF 持久化记录服务器执行的所有写操作命令，并在服务器启动时，通过重新执行这些命令来还原数据集。	

Redis 还可以同时使用 AOF 持久化和 RDB 持久化。 在这种情况下， 当 Redis 重启时， 它会优先使用 AOF 文件来还原数据集， 因为 AOF 文件保存的数据集通常比 RDB 文件所保存的数据集更完整。

## RDB 优缺点
优：故障恢复的时候特别快，最大化Redis性能；直接fork一个子进程，之后的所有保存工作全交给子进程；支持的功能更多。

缺：如果在未保存快照的时候故障，会丢失部分数据；子进程在fork的时候会非常影响性能；可能会造成客户端连接的停顿。

## AOF 优缺点
优：数据相比RDB可能更完整一些，因为是每秒写入一次，最多丢一秒的数据；操作追加到日志文件，可重写；
持久化记录服务器执行的所有写操作命令，并在服务器启动时，通过重新执行这些命令来还原数据集。新命令会被追加到文件的末尾。 
	Redis 还可以在后台对 AOF 文件进行重写（rewrite），使得 AOF 文件的体积不会超出保存数据集状态所需的实际大小。
	（什么是重写：set a 1，set a 2 set a 3，只记录set a 3）

缺：体积大于RDB，恢复速度慢于RDB

# Rrdis 主从原理

	1、当从库和主库建立MS关系后，会向主数据库发送PSYNC命令；
	2、主库接收到PSYNC命令后会开始在后台保存快照（RDB持久化过程），并将期间接收到的写请求写到缓存区；
	3、当快照完成后，主Redis会将快照文件和所有缓存的写命令发送给从Redis；
	4、从Redis接收到后，会载入快照文件并且执行收到的缓存的命令；
	5、主Redis每当接收到写命令时就会将命令发送从Redis，从而保证数据的一致；


# Redis 优化

更改端口
	
	port 6379		

设置密码

	requirepass XXXXXX

绑定地址

	bind 10.0.0.10

后台运行

	daemonize yes

日志级别

	loglevel warning

日志位置

	logfile "/var/log/redis_6379.log"

持久化

建议master关闭，slave开启

	save 900 1
	save 300 10
	save 60 10000                  

开启只读

	slave-read-only yes

慢查询

	slowlog-log-slower-than 5000

最大内存

	maxmemory 5gb

# 数据淘汰机制

	volatile-lru：使用LRU算法进行数据淘汰（淘汰上次使用时间最早的，且使用次数最少的key），只淘汰设定了有效期的key
	allkeys-lru：使用LRU算法进行数据淘汰，所有的key都可以被淘汰
	volatile-random：随机淘汰数据，只淘汰设定了有效期的key
	allkeys-random：随机淘汰数据，所有的key都可以被淘汰
	volatile-ttl：淘汰剩余有效期最短的key