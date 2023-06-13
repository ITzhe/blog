---
title: "LetsEncrypt"
date: 2017-06-13T10:59:21+08:00
draft: false
tags: ["HTTPS"]
---

---

在全民HTTPS的大趋势之下，Let's Encrypt可是功不可没，网上文档也有很多，本身很简单的东西，网上文档比17年初已经多了很多很多，但是没想到水平参差不齐，部署到一半就不行了，简直是坑爹，就16年的老技术了，简单的几个步骤还能报错？！！！

官方GitHub地址：https://github.com/Neilpang/acme.sh

---


安装acme.sh脚本

``` shell     	
curl  https://get.acme.sh | sh
# 注册账户    
~/.acme.sh/acme.sh --register-account -m bob1317581669@gmail.com
[Wed Feb 22 11:01:51 CST 2023] No EAB credentials found for ZeroSSL, let's get one
[Wed Feb 22 11:01:55 CST 2023] Registering account: https://acme.zerossl.com/v2/DV90
[Wed Feb 22 11:02:02 CST 2023] Registered
[Wed Feb 22 11:02:03 CST 2023] ACCOUNT_THUMBPRINT='yiMmaNSo-A27AG-jSqTkWrKKs7PgL7X9rPXApgxxxxx'
```

# 单域名证书

验证域名所有权

    acme.sh --issue -d cmdb.caizhe.org --nginx

安装证书

（其实证书已经下来了，就在acme的目录下面，但是你不想放在这里话，可以执行这一步）

```shell
[root@Bob-blog conf]# acme.sh --installcert -d cmdb.caizhe.org \
--keypath /application/nginx/conf/cmdb_ssl/cmdb.caizhe.org.key \
--fullchainpath /application/nginx/conf/cmdb_ssl/cmdb.caizhe.org.cer \
--reloadcmd "/application/nginx/sbin/nginx -s reload"
```

查看域名情况

```shell
[root@Bob-blog conf]# acme.sh --list
Main_Domain      KeyLength  SAN_Domains  Created                       Renew
cmdb.caizhe.org  ""         no           Wed Jun  5 09:19:13 UTC 2019  Sun Aug  4 09:19:13 UTC 2019
```

域名更新(之后跑个定时就行了)

    acme.sh --renew -d cmdb.caizhe.org --force

# 通配符证书

``` bash
export Ali_Key="LTAI4FyNQRVTRaGc1xxxxx"
export Ali_Secret="cE5Nhz8lRgCZ2lLxLP3ADjhIxxxxx"

~/.acme.sh/acme.sh  --issue --dns dns_ali -d 'caizhe.org' -d '*.caizhe.org'
```

通配符的https必须是用DNS模式，目前支持阿里DNS和DNSpod；
    
如果你是用的DNS 有支持的API接口，它会自己做验证和更新，

---
关于这个Let's Encrypt 我现在已经全站使用了近两年的时间了，没什么问题，大家可以放心使用。

---
certbot 更新通配符

    certbot-auto --server https://acme-v02.api.letsencrypt.org/directory -d "*.xxx.com" --manual --preferred-challenges dns-01 certonly

---
附录Nginx配置

``` shell
server {
        listen      80;
        server_name  cmdb.caizhe.org;
    
    	location /.well-known {
            alias /application/nginx/html/cmdb/.well-known;
    	}

        rewrite ^(.*) https://$server_name$1 last;
        error_page 497 https://$server_name$request_uri;
        
	}

server {
    listen 443 ssl;

    server_name cmdb.caizhe.org;
	
	ssl_certificate              /root/.acme.sh/cmdb.caizhe.org/cmdb.caizhe.org.cer;
	ssl_certificate_key          /root/.acme.sh/cmdb.caizhe.org/cmdb.caizhe.org.key;
	ssl_ciphers                  EECDH+CHACHA20:EECDH+CHACHA20-draft:EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256::!MD5;
	ssl_protocols                TLSv1 TLSv1.1 TLSv1.2;
	ssl_prefer_server_ciphers    on;
	#ssl_session_cache            builtin:1000 shared:SSL:10m;
	#ssl_session_timeout          1d;
	#ssl_session_tickets          on;

    location / {
            root   html/cmdb;
            index  index.html index.htm;
    }
}
```
