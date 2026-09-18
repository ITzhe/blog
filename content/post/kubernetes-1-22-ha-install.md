---
title: "High-Availability Kubernetes 1.22 Installation"
date: 2023-03-13T11:51:59+08:00
draft: false
slug: "kubernetes-1-22-ha-install"
tags: ["K8S"]
---

| Component | Version |
|  ----  | ----  |
| OS | Ubuntu 18 |
| k8s | 1.22 |
| kubeVIP | 0.5 |
| nginx-ingress | 1.3.1 |
---

Disable the firewall:

    ufw disable

Set the hostname:

```shell
hostnamectl  set-hostname master1.innovsharing.com
```

Set the hosts file:

```shell
172.20.55.100   api.k8s.local
172.20.55.46    master1.innovsharing.com
```

Enable kernel IPv4 forwarding:

```shell
cat /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
```

`bridge-nf` lets netfilter filter IPv4/ARP/IPv6 packets on a Linux bridge. For example, with `net.bridge.bridge-nf-call-iptables=1`, a layer-2 bridge forwarding packets will also have them filtered by iptables' FORWARD rules. The common options are:

net.bridge.bridge-nf-call-arptables: whether to filter ARP packets on the bridge in arptables FORWARD\
net.bridge.bridge-nf-call-ip6tables: whether to filter IPv6 packets in the ip6tables chains\
net.bridge.bridge-nf-call-iptables: whether to filter IPv4 packets in the iptables chains\
net.bridge.bridge-nf-filter-vlan-tagged: whether to filter VLAN-tagged packets in iptables/arptables.

Enable IPVS support:

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

Reboot the server, then run `lsmod | grep -e ip_vs -e nf_conntrack_ipv4` to check that it is enabled:

```shell
ip_vs_sh               16384  0
ip_vs_wrr              16384  0
ip_vs_rr               16384  0
ip_vs                 155648  6 ip_vs_rr,ip_vs_sh,ip_vs_wrr
nf_conntrack          139264  1 ip_vs
nf_defrag_ipv6         24576  2 nf_conntrack,ip_vs
libcrc32c              16384  2 nf_conntrack,ip_vs
```

Install IPVS:

```shell
apt-get install -y ipset ipvsadm
```

Install containerd:

```shell
wget https://github.com/containerd/containerd/releases/download/v1.6.8/cri-containerd-cni-1.6.8-linux-amd64.tar.gz
# Or download from a mirror:
# wget https://download.fastgit.org/containerd/containerd/releases/download/v1.5.5/cri-containerd-cni-1.5.5-linux-amd64.tar.gz

tar -C / -xzf cri-containerd-cni-1.6.8-linux-amd64.tar.gz

mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
```

Configure containerd — the file lives at `/etc/containerd/config.toml`:

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

Start containerd:

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

Install kube-VIP:

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

Contents of `kube-vip.yaml`:

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

Install kubeadm:

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

Generate the Kubernetes installation manifest:

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
  advertiseAddress: 172.20.55.46   # this machine's IP address
  bindPort: 6443
nodeRegistration:
  criSocket: /run/containerd/containerd.sock    # the containerd Unix socket
  imagePullPolicy: IfNotPresent
  name: master1    # node name
  taints: null
---
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
mode: ipvs  # kube-proxy mode
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
imageRepository: registry.aliyuncs.com/google_containers    # Aliyun mirror
kind: ClusterConfiguration
kubernetesVersion: 1.22.9
controlPlaneEndpoint: 172.20.55.100:6443  # control plane endpoint address
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

Pull the images:

```shell
kubeadm config images pull --config kubeadm.yaml
# coreDNS will fail with "not found"; you can tag it manually
ctr -n k8s.io i pull docker.io/coredns/coredns:1.8.4
ctr -n k8s.io i tag docker.io/coredns/coredns:1.8.4 registry.aliyuncs.com/k8sxio/coredns:v1.8.4


kubeadm init --upload-certs --config kubeadm.yaml

```

# Nginx-Ingress

Download: <https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.3.1/deploy/static/provider/cloud/deploy.yaml>

Make the controller use the host network (Deployment):

```shell
        ports:
        - containerPort: 80
          name: http
          hostPort: 80          # added
          protocol: TCP
        - containerPort: 443
          name: https
          hostPort: 443         # added
          protocol: TCP
          
    spec:
      hostNetwork: true         # use the host network throughout
      containers:
```

Change the DNS policy:

```shell
    dnsPolicy: ClusterFirstWithHostNet
```

Switch to a domestic mirror:

        image: registry.aliyuncs.com/google_containers/nginx-ingress-controller:v1.3.1
        
        image: registry.aliyuncs.com/google_containers/kube-webhook-certgen:v1.3.1
        
        image: registry.aliyuncs.com/google_containers/kube-webhook-certgen:v1.3.1

Tomcat test:

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

A regular Service:
generates a `servicename.namespace.svc.cluster.local` domain name that resolves to the Service's ClusterIP. Calls between Pods can shorten this to `servicename.namespace`, and if they are in the same namespace you can even just use `servicename`.

Headless Service:
a headless service has `clusterIP` set to `None`. It resolves to the list of IPs of the selected Pods, and you can also reach a specific Pod via `podname.servicename.namespace.svc.cluster.local`.
