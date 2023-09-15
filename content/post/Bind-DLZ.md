---
title: "Bind-DLZ"
date: 2018-08-02T17:44:11+08:00
draft: false
tags: ["DNS"] 
---

安装依赖：

    yum install openssl-devel -y 
    yum groupinstall "Development Tools" -y

数据库安装：

    yum install mariadb-server mariadb-devel -y
    systemctl start mariadb
    
删掉一些空用户，否则会报错

    delete from mysql.user where user='';
    create database bind;

安装bind
    
    tar xf bind-9.11.5.tar.gz
    cd bind-9.11.5/
    ./configure --with-dlz-mysql --enable-largefile --enable-threads=no --prefix=/usr/local/bind --with-openssl 
    # 我试了开线程，但是会报错，所以还是单进程，对DNS的查询操作都是在从库，主库只负责写入和修改操作然后同步到从库，从库直接使用dns的配置文件，所以效率并不影响
    make -j 4
    make install
    groupadd -r named
    useradd -s /sbin/nologin -M -r -g named named
    chown -R named:named /usr/local/bind 
    echo "export PATH=${PATH}:/usr/local/bind/sbin/:/usr/local/bind/bin/" >> /etc/profile
    source /etc/profile
    
配置bind

    cd /usr/local/bind/etc/
    rndc-confgen -r /dev/urandom >rndc.conf         #如果报错直接换成 rndc-confgen >rndc.conf
    mkdir /var/named/
    wget http://www.internic.net/domain/named.root      # 下载定义域服务节点
    chown -R named:named /var/named/

创建配置文件 named.conf

    [root@linux-node3 etc]# cat named.conf 
    options {
            directory "/var/named/";
            recursion yes;
            listen-on port 53    { any; };
            dump-file "/var/named/data/cache_dump.db";
            statistics-file "/var/named/data/named_stats.txt";
            allow-query { any; };
            blackhole { none; };
     };

# 启动并测试

    named -u named -n 1 -c /usr/local/bind/etc/named.conf
    netstat -lntup|grep 53
    dig www.baidu.com @127.0.0.1

# 配置DLZ

    create database bind;

建表

    CREATE TABLE IF NOT EXISTS `dns_records` (
      `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
      `zone` varchar(255) NOT NULL,
      `host` varchar(255) NOT NULL DEFAULT '@',
      `type` enum('A','MX','CNAME','NS','SOA','PTR','TXT','AAAA','SVR','URL') NOT NULL,
      `data` varchar(255) DEFAULT NULL,
      `ttl` int(11) NOT NULL DEFAULT '3600',
      `mx_priority` int(11) DEFAULT NULL,
      `view`  enum('any', 'Telecom', 'Unicom', 'CMCC', 'ours') NOT NULL  DEFAULT "any" ,
      `priority` tinyint UNSIGNED NOT NULL DEFAULT '255',
      `refresh` int(11) NOT NULL DEFAULT '28800',
      `retry` int(11) NOT NULL DEFAULT '14400',
      `expire` int(11) NOT NULL DEFAULT '86400',
      `minimum` int(11) NOT NULL DEFAULT '86400',
      `serial` bigint(20) NOT NULL DEFAULT '2015050917',
      `resp_person` varchar(64) NOT NULL DEFAULT 'ddns.net',
      `primary_ns` varchar(64) NOT NULL DEFAULT 'ns.ddns.net.',
      PRIMARY KEY (`id`),
      KEY `type` (`type`),
      KEY `host` (`host`),
      KEY `zone` (`zone`)
    ) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

	CREATE TABLE `dns_xfr` (
	  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
	  `zone` varchar(255) NOT NULL,
	  `client` varchar(255) NOT NULL,
	  PRIMARY KEY (`id`),
	  KEY `zone` (`zone`),
	  KEY `client` (`client`)
	) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;

创建用户

    grant all privileges on bind.* to named@'%' identified by "named";
    flush privileges;

named.conf 配置DLZ
    
	dlz "myzone" {
	        database "mysql
	           {host=192.168.56.11 port=3306 ssl=false dbname=bind user=named pass=named}
	           {SELECT zone FROM dns_records WHERE zone = '$zone$' LIMIT 1}
	           {SELECT ttl, type, mx_priority, IF(type = 'TXT', CONCAT('\"',data,'\"'), data) AS data FROM dns_records WHERE zone = '$zone$' AND host = '$record$' AND type <> '
	SOA' AND type <> 'NS'}
	           {SELECT ttl, type, data, primary_ns, resp_contact, serial, refresh, retry, expire, minimum FROM dns_records WHERE zone = '$zone$' AND (type = 'SOA' OR type='NS')
	}
	           {SELECT ttl, type, host, mx_priority, IF(type = 'TXT', CONCAT('\"',data,'\"'), data) AS data, resp_contact, serial, refresh, retry, expire, minimum FROM dns_reco
	rds WHERE zone = '$zone$' AND type <> 'SOA'}
	           {SELECT zone FROM dns_xfr WHERE ( zone='$zone$' OR zone='*' ) AND client = '$client$' LIMIT 1}";
	};



插入数据：

dns_records：

    insert into bind.dns_records (zone, host, type, data, ttl) VALUES ('test.info', 'www', 'A', '1.1.1.1', '60');
    insert into bind.dns_records (zone, host, type, data, ttl) VALUES ('test.info', 'bbs', 'A', '1.1.1.1', '60');

dns_xfr：

	1	*	10.31.63.30
	2	*	10.31.63.30
	3	*	192.168.56.12

重启bind服务并重新测试

    named -u named -n 1 -c /usr/local/bind/etc/named.conf 
    netstat -lntup|grep 53
    dig @127.0.0.1
    dig www.test.info @127.0.0.1
    dig bbs.test.info @127.0.0.1


# 从库

named.conf

	options {
	        directory "/usr/local/bind/etc/";
	        recursion yes;
	        listen-on port 53    { any; };
	        dump-file "/var/named/data/cache_dump.db";
	        statistics-file "/var/named/data/named_stats.txt";
	        allow-query { any; };
	 };
	
	key "rndc-key" {
	        algorithm hmac-md5;
	        secret "J+jRGi+v0DvKOoUoY6pWhQ==";
	};
	
	controls {
	        inet 127.0.0.1 port 953
	        allow { any; } keys { "rndc-key"; };
	};
	
	include "/usr/local/bind/etc/view.conf";


view.conf

	view "View" {
	    zone "."  IN {
	    	type hint;
	    	file "named.root";
	    };
	
	    zone "u.com" IN {
	         type    slave;
	         masters { 192.168.56.11; };
	         file    "slaves/u.com.zone";
	    };
	};

---
附带一份企业级主库配置文件

	options {
	        listen-on port 53 { any; };
	        listen-on-v6 port 53 { none; };
	        directory     "/usr/local/bind-dlz/var/named";
	        dump-file     "/usr/local/bind-dlz/var/named/data/cache_dump.db";
	        statistics-file "/usr/local/bind-dlz/var/named/data/named_stats.txt";
	        memstatistics-file "/usr/local/bind-dlz/var/named/data/named_mem_stats.txt";
	        //max-cache-size 1024m;
	        zone-statistics yes;
	        tcp-clients 80000;
	        stacksize   1000m;
	        clients-per-query   100000;
	        max-clients-per-query   100000;
	        recursion yes;
	        version "1.0.0";
	        dnssec-enable no;
	        dnssec-validation no;
	        bindkeys-file "/etc/bind-dlz/named.iscdlv.key";
	        managed-keys-directory "/usr/local/bind-dlz/var/named/dynamic";
	        pid-file "/usr/local/bind-dlz/var/run/named.pid";
	        session-keyfile "/usr/local/bind-dlz/var/run/session.key";
	
	        masterfile-format text;
	        serial-query-rate 1000;
	        transfers-out 20000;
	        empty-zones-enable no;
	        request-ixfr no;
	
	        allow-update { none; };
	        allow-update-forwarding { none; };
	        allow-query     { any; };
	        allow-query-cache { any ;};
	        allow-transfer { slave_list; };
	        allow-recursion { any; };
	        #allow-recursion { any; };
	        notify yes;
	
	        allow-notify { slave_list; };
	
	        forwarders { 114.114.114.114;119.29.29.29; };
	
	};
	
	
	zone "." IN {
	    type hint;
	    file "named.ca";
	};
	
	include "/etc/bind-dlz/named.rfc1912.zones";
	include "/etc/bind-dlz/named.root.key";
	include "/etc/bind-dlz/rndc.key";
	
	
	key "TSIG-key" {
	        algorithm hmac-md5;
	        secret "J+jRGi+v0DvKOoUoY6pWhQ==";
	};
	
	controls {
	      inet 127.0.0.1 port 953
	      allow { any; } keys { "rndc-key"; };
	};
	
	statistics-channels {
	        inet 127.0.0.1 port 8653 allow { 127.0.0.1; };
	};
	
	################### log ########################
	logging {
	        channel default_debug {
	                file "data/named.run";
	                severity dynamic;
	        };
	};
	
	
	################### acl ########################
	acl "lan_list" {
	        172.16.0.0/12;
	        192.168.0.0/16;
	        10.0.0.0/8;
	        127.0.0.1;
	};
	
	acl "slave_list" {
	        172.16.1.1;
	        172.16.1.252;
	        10.10.20.21;
	        10.10.20.22;
	        192.168.56.12;
	};
	
	
	
	################### zone ########################
	dlz "myzone" {
	        database "mysql
	           {host=192.168.56.11 port=3306 ssl=false dbname=bind user=named pass=named}
	           {SELECT zone FROM dns_records WHERE zone = '$zone$' LIMIT 1}
	           {SELECT ttl, type, mx_priority, IF(type = 'TXT', CONCAT('\"',data,'\"'), data) AS data FROM dns_records WHERE zone = '$zone$' AND host = '$record$' AND type <> 'SOA' AND type <> 'NS'}
	           {SELECT ttl, type, data, primary_ns, resp_contact, serial, refresh, retry, expire, minimum FROM dns_records WHERE zone = '$zone$' AND (type = 'SOA' OR type='NS')}
	           {SELECT ttl, type, host, mx_priority, IF(type = 'TXT', CONCAT('\"',data,'\"'), data) AS data, resp_contact, serial, refresh, retry, expire, minimum FROM dns_records WHERE zone = '$zone$' AND type <> 'SOA'}
	           {SELECT zone FROM dns_xfr WHERE ( zone='$zone$' OR zone='*' ) AND client = '$client$' LIMIT 1}";
	};