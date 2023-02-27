---
title: "Kubectl管理多套k8s"
date: 2023-02-27T15:59:25+08:00
slug: "Hugo Slug"
draft: false
---

注意：

两套k8s集群必须版本一致，自己试验1.13和1.15不通用。

具体使用方法：

```shell
[root@bogon ~]# kubectl get node --kubeconfig=/root/.kube/config
NAME    STATUS     ROLES    AGE    VERSION
bogon   NotReady   master   122m   v1.15.1
[root@bogon ~]# kubectl get node --kubeconfig=/root/.kube/config1
NAME           STATUS   ROLES    AGE    VERSION
k8s-master01   Ready    master   320d   v1.15.1
k8s-master02   Ready    master   320d   v1.15.1
k8s-master03   Ready    master   320d   v1.15.1
k8s-node1      Ready    <none>   320d   v1.15.1
```
