---
title: "Installing Elasticsearch with Docker"
date: 2023-06-14T14:29:17+08:00
draft: false
slug: "docker-elasticsearch"
tags: ["docker"]
---

| OS | Ubuntu 18 |
| :--- | :-------- |
| ES version | 8.10.1    |

Since 8.0, Elasticsearch requires HTTPS for inter-node cluster communication, so an SSL certificate has to be generated first.

You can start a single-node ES instance and use its command line to generate the certificate files.

Single-node ES startup command:

```bash
docker run -d \
    --name elasticsearch \
    -e "discovery.type=single-node"
    -e ELASTIC_PASSWORD=elastic \
    elasticsearch:8.10.1
```

Enter the container and generate the certificates.

CA certificate:

    elasticsearch-certutil ca		# press enter for every prompt; this produces elastic-stack-ca.p12

Private key certificate:

    elasticsearch-certutil cert --ca elastic-stack-ca.p12		# press enter for every prompt

Copy the certificate files out of the container and delete them:

ES configuration file — copy it to the other nodes as well:

    cluster.name: elasticsearch-cluster
    node.name: node1					# remember to change the node name
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

    # Whether cross-origin requests are allowed
    http.cors.enabled: true

    # "*" means any origin is allowed; you can also list specific domains or use a regex.
    http.cors.allow-origin: "*"

    # Headers allowed in cross-origin requests
    http.cors.allow-headers: Authorization

    # Whether to return the Access-Control-Allow-Credentials header
    http.cors.allow-credentials: true

    # Enable x-pack
    xpack.security.enabled: true
    # Enable SSL
    xpack.security.transport.ssl.enabled: true
    xpack.security.transport.ssl.verification_mode: certificate
    xpack.security.transport.ssl.client_authentication: required

    # Point at the CA certificate you generated
    xpack.security.transport.ssl.keystore.path: certs/elastic-certificates.p12
    xpack.security.transport.ssl.truststore.path: certs/elastic-certificates.p12
    xpack.security.authc.api_key.enabled: true

Startup command:

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

Test command: `curl -k --user elastic:elastic -XGET http://127.0.0.1:9200/_cat/indices?v`

***

Reference: <https://www.zsjweblog.com/2022/03/09/elasticsearch8-1-0%e9%9b%86%e7%be%a4%e6%90%ad%e5%bb%ba/>
