---
title: "Calling the Kubernetes API"
date: 2023-06-13T10:51:32+08:00
draft: false
slug: "kubernetes-api-calls"
tags: ["K8S"]
---

There are three ways to call the apiserver:

1. Use the official SDK;
2. From inside a Pod, use the service account token over port 443 — this gives better permission control and is easier to migrate (recommended);
3. Send requests directly to port 6443.

---
# Official SDK

The official GitHub has support for many languages: Go, Java, Perl, Ruby. There are plenty of simple examples, so I will not belabor the point — just Google it.

Python SDK: https://github.com/kubernetes-client/python


# Calling from inside a Pod

Fetch the token first, then issue the request against the apiserver.

``` shell
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl --cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt -H "Authorization: Bearer $TOKEN" -s  https://10.96.0.1:443/api/v1/namespaces/default/pods/
```

Reference: https://blog.csdn.net/russle/article/details/105333738

# Calling port 6443

Shell version:

```shell
curl https://192.168.1.100:6443/api/v1/nodes \
--cacert /etc/kubernetes/pki/ca.crt \
--cert /etc/kubernetes/pki/apiserver-kubelet-client.crt \
--key /etc/kubernetes/pki/apiserver-kubelet-client.key
```

Python version:

```
url = "https://ip:6443/api/v1/nodes/unis6"
try:
    res = requests.get(url, verify="/etc/kubernetes/pki/ca.pem",
    cert=("/etc/kubernetes/pki/apiserver-kubelet-client.crt","/etc/kubernetes/pki/apiserver-kubelet-client.key"),timeout=15)
except Exception as e: 
    print(e)
else:
  print("ok")
```

---
Some ways to call the metrics endpoint:
https://blog.csdn.net/u014106644/article/details/84839055
