---
title: "Nginx Tuning"
date: 2016-03-02T20:46:18+08:00
draft: false
slug: "nginx-tuning"
tags: ["Tuning", "Nginx"]
---

Nginx tuning splits into two directions: performance optimization and security hardening.

## Performance optimization

Enable gzip compression:

    gzip on;
    gzip_min_length  1k;
    gzip_buffers     4 32k;
    gzip_http_version 1.1;
    gzip_comp_level 2;
    gzip_types  text/css text/js text/xml application/javascript;
    gzip_vary on;

Use expires caching:

        location ~^/(images|javascript|js|css|flash|media|static)/ {
          expires 30d;
        }
    
    	 location ~ .*\.(gif|jpg|jpeg|png|bmp|swf)$
    	{
    	      expires      3650d;
    	}


Use the epoll model:

	use epoll;

Configure multiple worker processes:

	equal to the number of CPU cores, or CPU cores x2

Tune the max connections per worker process:

	worker_connections  20480；

Tune the max open files per process:

	worker_rlimit_nofile 65535;

Set connection timeouts:

	keepalive_timeout  300;
	
	Java applications should use long connections where possible; PHP applications should prefer short connections, because Java applications consume more resources and time than PHP (though it ultimately depends on the workload).

Client request header timeout and size:

	client_header_timeout 15s;	
	client_header_buffer_size 10k;

Client request body timeout:

	client_header_timeout 15s;

Limit on upload size:

	client_max_body_size        10m;

Enable efficient file transfer mode:

	sendfile       on;
	tcp_nopush     on;
	aio            on;

Set buffers for the upstream proxy server:

	proxy_buffering on;
	proxy_buffer_size 64k;
	proxy_buffers   4 32k;
	proxy_busy_buffers_size 64k;
	proxy_temp_file_write_size 64k;

Set the client timeout:

	send_timeout 300s;

## Security hardening

Hide the version number:

	server_tokens off;

Change the default user and group:

	user    nginx;

Prevent parsing of specific file types in a given directory:

	location ~ ^/images/.*\.(php|php5|.sh|.pl|.py)$ 
	        { 
	     		 deny all; 
	        } 

Restrict access by IP or IP range:

	location / { 
		deny 192.168.1.1; 
		allow 192.168.1.0/24; 
		deny all; 
	}

Block specific IPs:

	if ($remote_addr = 10.0.0.2 ) {
		return 403;
	}

Reject requests for unregistered domains:

	if （$host !~ caizhe/.org$）{
		return 500;
	}
	
	server {
	    listen 80 default;
	    return 500;
	}

Rate limiting:

	http {	
	limit_req_zone $binary_remote_addr zone=ttlsa_com:10m rate=1r/s;
	
	server {
	limit_req zone=one burst=5;

Graceful error pages:

	error_page   500 501 502 503 504  https://caizhe.org;
	error_page 	 400 403 404 405 408 410 411 412 413 414 415 https://caizhe.org;

Run nginx as an unprivileged user
