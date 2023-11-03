---
title: "Docker安装ES"
date: 2023-06-14T14:29:17+08:00
draft: false
tags: ["docker"]
---


| 操作系统 | Ubuntu 18 |
| :--- | :-------- |
| ES版本 | 8.10.1    |

ES 从8.0之间集群通讯改成了必须使用https的方式，需要先生成SSL证书；

可以先跑一个单机的ES，然后通过单机ES的命令行生成证书文件

单机ES运行命令：

```bash
docker run -d \
    --name elasticsearch \
    -e "discovery.type=single-node"
    -e ELASTIC_PASSWORD=elastic \
    elasticsearch:8.10.1
```

进入容器，准备生成证书：

CA证书：

    elasticsearch-certutil ca		#一路回车默认即可，最后会生成elastic-stack-ca.p12的文件

私钥证书：

    elasticsearch-certutil cert --ca elastic-stack-ca.p12		#一路回车默认即可

将证书文件拷贝出容器之外并删掉

ES配置文件，并将配置文件拷贝到其他节点：

    cluster.name: elasticsearch-cluster
    node.name: node1					# 记得修改node名称
    network.host: 0.0.0.0
    http.port: 9200
    transport.port: 9300

    discovery.seed_hosts: 
        - 10.1.1.10:9300
    	- 10.1.1.20:9300
    	- 10.1.1.30:9300

    ## Bootstrap the cluster using an initial set of master-eligible nodes:
    cluster.initial_master_nodes: 
    	- node1
    	- node2
    	- node3

    # 是否支持跨域
    http.cors.enabled: true

    # 默认为*表示支持所有域名跨域访问，也可以指定域名跨域，或者使用正则表达式匹配。
    http.cors.allow-origin: "*"

    # 跨域允许设置的头信息
    http.cors.allow-headers: Authorization

    # 是否返回设置的跨域Access-Control-Allow-Credentials头
    http.cors.allow-credentials: true

    # 开启x-pack
    xpack.security.enabled: true
    # 开启ssl认证
    xpack.security.transport.ssl.enabled: true
    xpack.security.transport.ssl.verification_mode: certificate
    xpack.security.transport.ssl.client_authentication: required

    # 配置生成的ca证书，这里的路径可以根据
    xpack.security.transport.ssl.keystore.path: certs/elastic-certificates.p12
    xpack.security.transport.ssl.truststore.path: certs/elastic-certificates.p12
    xpack.security.authc.api_key.enabled: true

启动命令：

```bash
docker run -d \
    --name elasticsearch \
    --restart=always \
	--network=host \
    -e ES_JAVA_OPTS="-Xms2g -Xmx2g" \
    -e ELASTIC_PASSWORD=elastic \
    -p 9200:9200 \
    -p 9300:9300 \
    -v /data/config/es/certs/:/usr/share/elasticsearch/config/certs/ \
    -v /data/config/es/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml \
    elasticsearch:8.10.1
```

测试命令：curl -k --user elastic\:elastic -XGET [http://127.0.0.1:9200/\_cat/indices?v](http://172.20.55.50:9201/_cat/indices?v)

***

参考链接：<https://www.zsjweblog.com/2022/03/09/elasticsearch8-1-0%e9%9b%86%e7%be%a4%e6%90%ad%e5%bb%ba/>

