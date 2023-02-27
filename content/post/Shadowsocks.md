---
title: "Shadowsocks部署"
date: 2023-02-27T16:02:14+08:00
slug: "Hugo Slug"
draft: true
---

最近乘着双十一有优惠，买了台香港的服务器，之前一直用公司的，打算换成自己的，写篇博客记录一下，直接开始

系统：Ubuntu 18

```shell
apt-get update
apt-get install python-pip
pip install shadowsocks
apt-get install python-m2crypto
```

创建配置文件（默认不存在）
```shell
cat /etc/shadowsocks.json 
{
	"server": "0.0.0.0",
	"server_port": 13090,       # 服务的要开放的端口
	"local_port": 1080,         
	"password": "111111",       # 连接的密码
	"timeout": 600,
	"method": "aes-256-cfb",    # 加密算法（aes-256-gcm好像不行）
	"fast_open": false,
	"workers": 1,
	"prefer_ipv6": false
}
```

启动
```shell
ssserver -c /etc/shadowsocks.json -d start
```
如果启动报错：

```
AttributeError: /usr/lib/x86_64-linux-gnu/libcrypto.so.1.1: undefined symbol: EVP_CIPHER_CTX_cleanup
```

执行此命令：
```
sed -i "s#EVP_CIPHER_CTX_cleanup#EVP_CIPHER_CTX_reset#g" /usr/local/lib/python2.7/dist-packages/shadowsocks/crypto/openssl.py
```

---
可以去GitHub上下载最新的客户端
https://github.com/shadowsocks
---
BBR 加速

```shell
wget --no-check-certificate https://github.com/teddysun/across/raw/master/bbr.sh
 chmod +x bbr.sh
 ./bbr.sh
lsmod | grep bbr  //返回值如果有tcp_bbr模块，就说明bbr已经启动了。
```
---

连上之后可以先百度一下自己的IP，看看是不是改了。

---

参考连接：https://zinyan.com/?p=6
