---
title: "Let's Encrypt with acme.sh"
date: 2017-06-13T10:59:21+08:00
draft: false
slug: "letsencrypt-acme-sh"
tags: ["HTTPS"]
---

---

With HTTPS becoming the norm, Let's Encrypt has been a huge part of that. There are plenty of guides online and the process itself is simple — far more material exists now than in early 2017. Unfortunately the quality varies wildly: half the guides fail partway through. It is 2016 technology, and a few simple steps still manage to error out?!

Official GitHub: https://github.com/Neilpang/acme.sh

---


Install the acme.sh script:

``` shell     	
curl  https://get.acme.sh | sh
# register an account
~/.acme.sh/acme.sh --register-account -m bob1317581669@gmail.com
[Wed Feb 22 11:01:51 CST 2023] No EAB credentials found for ZeroSSL, let's get one
[Wed Feb 22 11:01:55 CST 2023] Registering account: https://acme.zerossl.com/v2/DV90
[Wed Feb 22 11:02:02 CST 2023] Registered
[Wed Feb 22 11:02:03 CST 2023] ACCOUNT_THUMBPRINT='yiMmaNSo-A27AG-jSqTkWrKKs7PgL7X9rPXApgxxxxx'
```

# Single-domain certificate

Verify domain ownership:

    acme.sh --issue -d cmdb.caizhe.org --nginx

Install the certificate:

(The certificate is already issued and sits in the acme directory, but if you do not want it there you can run this step.)

```shell
[root@Bob-blog conf]# acme.sh --installcert -d cmdb.caizhe.org \
--keypath /application/nginx/conf/cmdb_ssl/cmdb.caizhe.org.key \
--fullchainpath /application/nginx/conf/cmdb_ssl/cmdb.caizhe.org.cer \
--reloadcmd "/application/nginx/sbin/nginx -s reload"
```

Check the domain status:

```shell
[root@Bob-blog conf]# acme.sh --list
Main_Domain      KeyLength  SAN_Domains  Created                       Renew
cmdb.caizhe.org  ""         no           Wed Jun  5 09:19:13 UTC 2019  Sun Aug  4 09:19:13 UTC 2019
```

Renew the certificate (afterwards just add a cron job):

    acme.sh --renew -d cmdb.caizhe.org --force

# Wildcard certificate

``` bash
export Ali_Key="LTAI4FyNQRVTRaGc1xxxxx"
export Ali_Secret="cE5Nhz8lRgCZ2lLxLP3ADjhIxxxxx"

~/.acme.sh/acme.sh  --issue --dns dns_ali -d 'caizhe.org' -d '*.caizhe.org'
```

Wildcard certificates must use DNS validation. Aliyun DNS and DNSPod are currently supported.

If your DNS provider has a supported API, it handles the validation and updates itself.

---
I have now been running Let's Encrypt across the whole site for close to two years with no problems. You can use it without worry.

---
Updating a wildcard certificate with certbot:

    certbot-auto --server https://acme-v02.api.letsencrypt.org/directory -d "*.xxx.com" --manual --preferred-challenges dns-01 certonly

---
Appendix: Nginx configuration

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
