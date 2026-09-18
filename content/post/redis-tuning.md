---
title: "Redis Tuning"
date: 2017-03-02T20:52:54+08:00
draft: false
slug: "redis-tuning"
tags: ["Tuning", "Redis"]
---

# Redis persistence modes

Redis offers several levels of persistence:

	RDB persistence produces a point-in-time snapshot of the dataset at a configured interval.

	AOF persistence records every write command the server executes, and on startup replays them to rebuild the dataset.

Redis can use both AOF and RDB persistence at the same time. In that case, when Redis restarts it prefers the AOF file to rebuild the dataset, because the AOF file usually holds a more complete dataset than the RDB file.

## RDB pros and cons

Pros: very fast failover recovery; maximizes Redis performance; saving is handed off to a forked child process; more supported features.

Cons: if the server fails before a snapshot is saved, some data is lost; forking a child process is expensive; it can cause a pause in client connections.

## AOF pros and cons

Pros: the data may be more complete than with RDB, since it writes once per second and loses at most one second of data; operations are appended to a log file that can be rewritten. It records every write command the server executes and replays them on startup to rebuild the dataset. New commands are appended to the end of the file.

	Redis can also rewrite the AOF file in the background, so the file does not grow beyond the actual size needed to represent the dataset.
	(What is a rewrite? Given `set a 1`, `set a 2`, `set a 3`, only `set a 3` is kept.)

Cons: larger than RDB, and slower to restore.

# Redis replication

	1. Once a replica establishes a master-slave relationship with the master, it sends a PSYNC command to the master;
	2. On receiving PSYNC, the master starts saving a snapshot in the background (the RDB persistence process) and buffers any write requests received in the meantime;
	3. When the snapshot completes, the master sends the snapshot file and all buffered write commands to the replica;
	4. The replica loads the snapshot file and executes the buffered commands it received;
	5. From then on, every write command the master receives is forwarded to the replica, keeping the data consistent.


# Redis tuning

Change the port:

	port 6379		

Set a password:

	requirepass XXXXXX

Bind an address:

	bind 10.0.0.10

Run in the background:

	daemonize yes

Log level:

	loglevel warning

Log location:

	logfile "/var/log/redis_6379.log"

Persistence:

	recommended off on the master, on for replicas

	save 900 1
	save 300 10
	save 60 10000                  

Enable read-only mode:

	slave-read-only yes

Slow query:

	slowlog-log-slower-than 5000

Max memory:

	maxmemory 5gb

# Eviction policies

	volatile-lru: evict using the LRU algorithm (evicting the key that was used least recently and least often), only among keys with a TTL set
	allkeys-lru: evict using the LRU algorithm, across all keys
	volatile-random: evict randomly, only among keys with a TTL set
	allkeys-random: evict randomly, across all keys
	volatile-ttl: evict the key with the shortest remaining TTL
