---
title: "Nginx优化"
date: 2023-03-02T20:46:18+08:00
draft: false
tags: ["调优"]
---

nginx 的优化分为两个小方向：性能优化 & 安全优化

## 性能优化

开启gzip压缩

    gzip on;
    gzip_min_length  1k;
    gzip_buffers     4 32k;
    gzip_http_version 1.1;
    gzip_comp_level 2;
    gzip_types  text/css text/js text/xml application/javascript;
    gzip_vary on;

使用expires 缓存

        location ~^/(images|javascript|js|css|flash|media|static)/ {
          expires 30d;
        }
    
    	 location ~ .*\.(gif|jpg|jpeg|png|bmp|swf)$
    	{
    	      expires      3650d;
    	}


使用epoll模型

	use epoll;

配置多个work进程

	与CPU的核数相等 or CPU的核数 X2

调整当进程的最大连接数

	worker_connections  20480；

调整进程可打开的的最大文件数

	worker_rlimit_nofile 65535;

设置连接超时

	keepalive_timeout  300;
	
	JAVA应用经量使用长连接、如果是PHP的尽量使用短连接，因为Java应用要消耗的资源和时间要比PHP跟多（具体依然要看业务）

客户端请求头超时时间/大小

	client_header_timeout 15s;	
	client_header_buffer_size 10k;

客户端请求主体超时时间

	client_header_timeout 15s;

用户上传大小的限制

	client_max_body_size        10m;

开启高效文件传输模式

	sendfile       on;
	tcp_nopush     on;
	aio            on;

为后端代理服务器设置缓冲区

	proxy_buffering on;
	proxy_buffer_size 64k;
	proxy_buffers   4 32k;
	proxy_busy_buffers_size 64k;
	proxy_temp_file_write_size 64k;

制定客户端的超时时间

	send_timeout 300s;

## 安全优化

隐藏版本号

	server_tokens off;

更改默认用户组

	user    nginx;

静止解析制定目录下的特定文件

	location ~ ^/images/.*\.(php|php5|.sh|.pl|.py)$ 
	        { 
	     		 deny all; 
	        } 

限制及指定IP或IP段访问

	location / { 
		deny 192.168.1.1; 
		allow 192.168.1.0/24; 
		deny all; 
	}

限制非法IP
	
	if ($remote_addr = 10.0.0.2 ) {
		return 403;
	}

禁止非法域名解析访问

	if （$host !~ caizhe/.org$）{
		return 500;
	}
	
	server {
	    listen 80 default;
	    return 500;
	}

限制访问频率

	http {	
	limit_req_zone $binary_remote_addr zone=ttlsa_com:10m rate=1r/s;
	
	server {
	limit_req zone=one burst=5;

错误页面优雅显示
	
	error_page   500 501 502 503 504  https://caizhe.org;
	error_page 	 400 403 404 405 408 410 411 412 413 414 415 https://caizhe.org;

使用普通用户启动nginx