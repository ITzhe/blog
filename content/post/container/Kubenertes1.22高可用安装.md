---
title: "Kubenertes1.22高可用安装"
date: 2023-02-27T15:53:25+08:00
slug: "Hugo Slug"
draft: true
---

关闭防火墙

    ufw disable

设置主机名

```shell
hostnamectl  set-hostname master1.innovsharing.com
```

设置hosts

```shell
172.20.55.100   api.k8s.local
172.20.55.46    master1.innovsharing.com
```

开启内核IPV4转发

```shell
cat /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
```

bridge-nf 使得 netfilter 可以对 Linux 网桥上的 IPv4/ARP/IPv6 包过滤。比如，设置net.bridge.bridge-nf-call-iptables＝1后，二层的网桥在转发包时也会被 iptables的 FORWARD 规则所过滤。常用的选项包括：

net.bridge.bridge-nf-call-arptables：是否在 arptables 的 FORWARD 中过滤网桥的 ARP 包\
net.bridge.bridge-nf-call-ip6tables：是否在 ip6tables 链中过滤 IPv6 包\
net.bridge.bridge-nf-call-iptables：是否在 iptables 链中过滤 IPv4 包\
net.bridge.bridge-nf-filter-vlan-tagged：是否在 iptables/arptables 中过滤打了 vlan 标签的包。

开启IPVS支持

```shell
root@master1:~#  cat /etc/modules-load.d/k8s.conf
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
## use nf_conntrack instead of nf_conntrack_ipv4 for Linux kernel 4.19 and later
## nf_conntrack_ipv4
nf_conntrack

systemctl restart systemd-modules-load.service
```

重启服务器，然后执行`lsmod | grep -e ip_vs -e nf_conntrack_ipv4`,检查是否开启

```shell
ip_vs_sh               16384  0
ip_vs_wrr              16384  0
ip_vs_rr               16384  0
ip_vs                 155648  6 ip_vs_rr,ip_vs_sh,ip_vs_wrr
nf_conntrack          139264  1 ip_vs
nf_defrag_ipv6         24576  2 nf_conntrack,ip_vs
libcrc32c              16384  2 nf_conntrack,ip_vs
```

安装IPVS

```shell
apt-get install -y ipset ipvsadm
```

安装crontained

```shell
wget https://github.com/containerd/containerd/releases/download/v1.6.8/cri-containerd-cni-1.6.8-linux-amd64.tar.gz
# 或者国内下载：
# wget https://download.fastgit.org/containerd/containerd/releases/download/v1.5.5/cri-containerd-cni-1.5.5-linux-amd64.tar.gz

tar -C / -xzf cri-containerd-cni-1.6.8-linux-amd64.tar.gz

mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
```

配置crontained，文件位于/etc/containerd/config.toml

```shell
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
    SystemdCgroup = true


      [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
          endpoint = ["https://bqr1dr1n.mirror.aliyuncs.com"]
        [plugins."io.containerd.grpc.v1.cri".registry.mirrors."k8s.gcr.io"]
          endpoint = ["https://registry.aliyuncs.com/google_containers"]


sandbox_image = "registry.aliyuncs.com/k8sxio/pause:3.6"
```

启动crontained

```shell
systemctl daemon-reload
systemctl enable containerd --now

root@master1:~# ctr version
Client:
  Version:  v1.6.8
  Revision: 9cd3357b7fd7218e4aec3eae239db1f68a5a6ec6
  Go version: go1.17.13

Server:
  Version:  v1.6.8
  Revision: 9cd3357b7fd7218e4aec3eae239db1f68a5a6ec6
  UUID: 8804ad26-c5c3-4320-846a-b713c2307d5e
```

安装kube-VIP

```shell
mkdir -p /etc/kubernetes/manifests/

export VIP=172.20.55.100
export INTERFACE=eth0

ctr run --rm --net-host \
    docker.io/plndr/kube-vip:v0.5.0 \
    vip /kube-vip manifest pod \
    --interface $INTERFACE \
    --vip $VIP \
    --controlplane \
    --arp \
    --leaderElection | tee /etc/kubernetes/manifests/kube-vip.yaml 
    > /etc/kubernetes/manifests/kube-vip.yaml
    
```

kube-vip.yaml 内容

<details>
<summary>/etc/kubernetes/manifests/kube-vip.yaml</summary>

```shell
apiVersion: v1
kind: Pod
metadata:
  creationTimestamp: null
  name: kube-vip
  namespace: kube-system
spec:
  containers:
  - args:
    - manager
    env:
    - name: vip_arp
      value: "true"
    - name: port
      value: "6443"
    - name: vip_interface
      value: eth0
    - name: vip_cidr
      value: "32"
    - name: cp_enable
      value: "true"
    - name: cp_namespace
      value: kube-system
    - name: vip_ddns
      value: "false"
    - name: vip_leaderelection
      value: "true"
    - name: vip_leaseduration
      value: "5"
    - name: vip_renewdeadline
      value: "3"
    - name: vip_retryperiod
      value: "1"
    - name: vip_address
      value: 172.20.55.100
    - name: prometheus_server
      value: :2112
    image: ghcr.io/kube-vip/kube-vip:v0.5.0
    imagePullPolicy: Always
    name: kube-vip
    resources: {}
    securityContext:
      capabilities:
        add:
        - NET_ADMIN
        - NET_RAW
    volumeMounts:
    - mountPath: /etc/kubernetes/admin.conf
      name: kubeconfig
  hostAliases:
  - hostnames:
    - kubernetes
    ip: 127.0.0.1
  hostNetwork: true
  volumes:
  - hostPath:
      path: /etc/kubernetes/admin.conf
    name: kubeconfig
status: {}
```

</details>   
<br>

安装kubeadm

```shell
apt-get update && apt-get install -y apt-transport-https
curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | apt-key add - 
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
EOF

apt-get update
# apt-get install -y kubelet kubeadm kubectl
apt-get install  kubelet=1.22.9-00 kubeadm=1.22.9-00 kubectl=1.22.9-00

systemctl enable kubelet
```

生成K8S 安装配置清单文件

```shell
kubeadm config print init-defaults --component-configs KubeletConfiguration > kubeadm.yaml
```

<details>
<summary>kubeadm.yaml</summary>

```shell
apiVersion: kubeadm.k8s.io/v1beta3
bootstrapTokens:
- groups:
  - system:bootstrappers:kubeadm:default-node-token
  token: abcdef.0123456789abcdef
  ttl: 24h0m0s
  usages:
  - signing
  - authentication
kind: InitConfiguration
localAPIEndpoint:
  advertiseAddress: 172.20.55.46   # 本机IP地址
  bindPort: 6443
nodeRegistration:
  criSocket: /run/containerd/containerd.sock    # 使用 containerd的Unix socket 地址
  imagePullPolicy: IfNotPresent
  name: master1    # 节点名称
  taints: null
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: ipvs  # kube-proxy 模式
---
apiServer:
  timeoutForControlPlane: 4m0s
apiVersion: kubeadm.k8s.io/v1beta3
certificatesDir: /etc/kubernetes/pki
clusterName: kubernetes
controllerManager: {}
dns: {}
etcd:
  local:
    dataDir: /var/lib/etcd
imageRepository: registry.aliyuncs.com/google_containers    # 阿里云镜像站
kind: ClusterConfiguration
kubernetesVersion: 1.22.9
controlPlaneEndpoint: 172.20.55.100:6443  # 设置控制平面Endpoint地址
networking:
  dnsDomain: cluster.local
  serviceSubnet: 10.96.0.0/12
scheduler: {}
---
apiVersion: kubelet.config.k8s.io/v1beta1
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 0s
    enabled: true
  x509:
    clientCAFile: /etc/kubernetes/pki/ca.crt
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 0s
    cacheUnauthorizedTTL: 0s
cgroupDriver: systemd
clusterDNS:
- 10.96.0.10
clusterDomain: cluster.local
cpuManagerReconcilePeriod: 0s
evictionPressureTransitionPeriod: 0s
fileCheckFrequency: 0s
healthzBindAddress: 127.0.0.1
healthzPort: 10248
httpCheckFrequency: 0s
imageMinimumGCAge: 0s
kind: KubeletConfiguration
logging: {}
memorySwap: {}
nodeStatusReportFrequency: 0s
nodeStatusUpdateFrequency: 0s
resolvConf: /run/systemd/resolve/resolv.conf
rotateCertificates: true
runtimeRequestTimeout: 0s
shutdownGracePeriod: 0s
shutdownGracePeriodCriticalPods: 0s
staticPodPath: /etc/kubernetes/manifests
streamingConnectionIdleTimeout: 0s
syncFrequency: 0s
volumeStatsAggPeriod: 0s
root@master1:~#
```

</details>   
<br>

下载镜像

```shell
kubeadm config images pull --config kubeadm.yaml
# core DNS 会报错，找不到，可以打一个tag
ctr -n k8s.io i pull docker.io/coredns/coredns:1.8.4
ctr -n k8s.io i tag docker.io/coredns/coredns:1.8.4 registry.aliyuncs.com/k8sxio/coredns:v1.8.4


kubeadm init --upload-certs --config kubeadm.yaml

```

# Nginx-Ingress

下载地址：<https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.3.1/deploy/static/provider/cloud/deploy.yaml>

让控制器使用主机网络（Deployment）：

```shell
        ports:
        - containerPort: 80
          name: http
          hostPort: 80          # 新增加
          protocol: TCP
        - containerPort: 443
          name: https
          hostPort: 443         # 新增加
          protocol: TCP
          
    spec:
      hostNetwork: true         # 全部使用主机网络
      containers:
```

修改DNS策略：

```shell
    dnsPolicy: ClusterFirstWithHostNet
```

修改国内镜像：

        image: registry.aliyuncs.com/google_containers/nginx-ingress-controller:v1.3.1
        
        image: registry.aliyuncs.com/google_containers/kube-webhook-certgen:v1.3.1
        
        image: registry.aliyuncs.com/google_containers/kube-webhook-certgen:v1.3.1

Tomcat测试：

```yaml
root@OPS:/opt# cat 02-tomcat.yaml 
apiVersion: v1
kind: Service
metadata:
  name: tomcat
  namespace: default
spec:
  selector:
    app: tomcat
    release: canary
  ports:
  - name: http
    targetPort: 8080
    port: 8080
  - name: ajp
    targetPort: 8009
    port: 8009
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tomcat-deploy
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tomcat
      release: canary
  template:
    metadata:
      labels:
        app: tomcat
        release: canary
    spec:
      containers:
      - name: tomcat
        image: tomcat:8.5.34-jre8-alpine
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8080
          name: ajp
          containerPort: 8009

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-myapp
  namespace: default
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
  - host: www.example.com
    http:
      paths:
      - path: /
        pathType:  Prefix
        backend:
         service:
           name: tomcat
           port:
            number: 8080
```

普通的 Service：
会生成servicename.namespace.svc.cluster.local的域名，会解析到 Service 对应的 ClusterIP 上，在 Pod 之间的调用可以简写成servicename.namespace，
如果处于同一个命名空间下面，甚至可以只写成 servicename 即可访问

Headless Service：
无头服务，就是把 clusterIP 设置为 None 的，会被解析为指定 Pod 的 IP 列表，同样还可以通过podname.servicename.namespace.svc.cluster.local访问到具体的某一个 Pod。
