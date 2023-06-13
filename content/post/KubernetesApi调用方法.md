---
dtitle: "KubernetesApi调用方法"
date: 2023-06-12T18:26:20+08:00
draft: false
tags: "K8S"
---

apiserver调用分为3种：
1. 使用官方的SDK
2. 在Pod内部使用Token，使用443端口，权限控制的比较好，迁移也方便（推荐）
3. 对6443端口发起请求

---
# 官方SDK
官方的GitHub有很多语言的支持，有Go、Java、Perl、Ruby；
栗子也很多也很简单，这里我就不费口舌了，自行Google。

Python SDK地址：https://github.com/kubernetes-client/python


# Pod内部调用

内部先获取Token，然后发起请求对apiserver

``` shell
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl --cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt -H "Authorization: Bearer $TOKEN" -s  https://10.96.0.1:443/api/v1/namespaces/default/pods/
```

参考链接：https://blog.csdn.net/russle/article/details/105333738

# 6443 端口请求

Shell 版本：
```shell
curl https://192.168.1.100:6443/api/v1/nodes \
--cacert /etc/kubernetes/pki/ca.crt \
--cert /etc/kubernetes/pki/apiserver-kubelet-client.crt \
--key /etc/kubernetes/pki/apiserver-kubelet-client.key
```

Python 版本：
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
metrics 接口一些调用方法：
https://blog.csdn.net/u014106644/article/details/84839055
