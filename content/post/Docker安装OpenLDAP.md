---
title: "Docker安装OpenLDAP"
date: 2023-07-24T14:29:17+08:00
draft: false
tags: ["docker","LDAP"]
---

# 环境信息

| 系统版本      | Docker | LDAP   |
| :-------- | :----- | :----- |
| Ubuntu 18 | 20.10  | 2.4.57 |

# 安装OpenLDAP

```shell
docker run -d \
-p 389:389 \
--name openldap \
--restart=always \
--env LDAP_ORGANISATION="caizhe" \
--env LDAP_DOMAIN="caizhe.org" \
--env LDAP_ADMIN_PASSWORD="111111" \
osixia/openldap
```

# 安装web管理端（PHPLDAPadmin）

```bash
docker run -d \
--privileged \
-p 80:80 \
--name phpldapadmin \
--env PHPLDAPADMIN_HTTPS=false \
--env PHPLDAPADMIN_LDAP_HOSTS=192.168.1.100 \
osixia/phpldapadmin
```

## 测试命令：

```bash
ldapsearch -x -H ldap:/// -D "cn=admin,dc=caizhe,dc=org" -w 111111 -b "dc=caizhe,dc=org" -LLL
```

或者在容器里执行

```bash
ldapsearch -x -H ldap:/// -D "cn=admin,dc=caizhe,dc=org" -w 111111 -b "dc=caizhe,dc=org" -LLL
```

## 创建组

LDAP新建用户



建立用户之前先建立一个group

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%871.png)

选择default

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%872.png)

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%873.png)

这里可以随便选一个单位，后期还要改！

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%874.png)

确认无误提交即可，组算是创建完毕了

## 创建用户

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%875.png)

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%876.png)

![](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%877.png)

![](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%878.png)

![](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%879.png)

LDAP组和人员之前默认是不关联的，我们需要把刚才新建的用户添加到“dba-group”组里

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%8710.png)

![](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%8711.png)

最终的结果是这样的，“Update\~”提交即可  

用户已经加入这个组了，我们来看一下，重点是memberOf，咱们Jenkins对组授权就是通过读取memberOf这个字段来判断的，（很想问问作者为什么不能去读取DN，根据OU来判断）

![image.png](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/%E5%9B%BE%E7%89%8712.png)

# 密码策略

密码策略是一般是使用ppolicy，可以使用下面命令查看是否加载了ppolicy模块

```bash
root@openldap-host:/etc/ldap# slapcat -n 0 | grep -i module
dn: cn=module{0},cn=config
objectClass: olcModuleList
cn: module{0}
olcModulePath: /usr/lib/ldap
olcModuleLoad: {0}back_mdb
olcModuleLoad: {1}memberof
olcModuleLoad: {2}refint
structuralObjectClass: olcModuleList
olcAttributeTypes: {15}( 1.3.6.1.4.1.4754.1.99.1 NAME 'pwdCheckModule' DESC
 'Loadable module that instantiates "check_password() function' EQUALITY cas
 op AUXILIARY MAY pwdCheckModule )
```

没有的话需要ldapadd命令额外加载模块，新建一个ldif文件

```bash
cat load-ppolicy-mod.ldif
dn: cn=module{0},cn=config
changetype: modify
add: olcModuleLoad
olcModuleLoad: ppolicy.la
```

加载命令：

```bash
ldapadd -Y EXTERNAL -H ldapi:/// -f load-ppolicy-mod.ldif
```

检查是否加载成功

```bash
root@openldap-host:/etc/ldap# slapcat -n 0 | grep -i module
dn: cn=module{0},cn=config
objectClass: olcModuleList
cn: module{0}
olcModulePath: /usr/lib/ldap
olcModuleLoad: {0}back_mdb
olcModuleLoad: {1}memberof
olcModuleLoad: {2}refint
olcModuleLoad: {3}ppolicy.la
structuralObjectClass: olcModuleList
olcAttributeTypes: {15}( 1.3.6.1.4.1.4754.1.99.1 NAME 'pwdCheckModule' DESC
 'Loadable module that instantiates "check_password() function' EQUALITY cas
 op AUXILIARY MAY pwdCheckModule )
```

检查现有LDAP策略的数据库存储格式，发现均为mdb格式

```bash
root@openldap-host:/etc/ldap# ldapsearch -LLL -Y EXTERNAL -H ldapi:/// -b  cn=config olcDatabase | grep mdb
SASL/EXTERNAL authentication started
SASL username: gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth
SASL SSF: 0
dn: olcDatabase={1}mdb,cn=config
olcDatabase: {1}mdb
dn: olcOverlay={0}memberof,olcDatabase={1}mdb,cn=config
dn: olcOverlay={1}refint,olcDatabase={1}mdb,cn=config
```

创建默认密码策略的DN

```bash
root@openldap-host:/etc/ldap# cat pwpolicyoverlay.ldif
dn: olcOverlay=ppolicy,olcDatabase={1}mdb,cn=config
objectClass: olcOverlayConfig
objectClass: olcPPolicyConfig
olcOverlay: ppolicy
olcPPolicyDefault: cn=default,dc=caizhe,dc=org
olcPPolicyHashCleartext: TRUE
```

更新数据库

```bash
root@498d5b127557:/# ldapadd -Y EXTERNAL -H ldapi:/// -f pwpolicyoverlay.ldif
SASL/EXTERNAL authentication started
SASL username: gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth
SASL SSF: 0
adding new entry "olcOverlay=ppolicy,olcDatabase={1}mdb,cn=config"
```

添加默认策略规则

这里为了测试（密码过期设置了100秒，60秒前会有提醒）

```bash
cat ldap-pwpolicies.ldif
dn: cn=default,dc=caizhe,dc=org
objectClass: inetOrgPerson
objectClass: pwdPolicyChecker
objectClass: pwdPolicy
cn: pwpolicy
sn: pwpolicy
pwdAttribute: userPassword
pwdMinAge: 0
pwdMaxAge: 100
pwdInHistory: 5
pwdCheckQuality: 2
pwdMinLength: 8
pwdExpireWarning: 60
pwdGraceAuthNLimit: 3
pwdLockout: TRUE
pwdLockoutDuration: 0
pwdMaxFailure: 0
pwdFailureCountInterval: 0
pwdReset: TRUE
pwdMustChange: TRUE
pwdAllowUserChange: TRUE
pwdSafeModify: FALSE
```

更新 slapd 上的密码策略(创建一个默认的策略，名字叫default)

```bash
ldapadd -Y EXTERNAL -H ldapi:/// -f ldap-pwpolicies.ldif
SASL/EXTERNAL authentication started
SASL username: gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth
SASL SSF: 0
adding new entry "cn=default,dc=caizhe,dc=org"
```

## 测试

修改密码为不符合要求：

```bash
root@openldap-host:/etc/ldap# ldappasswd -H ldapi:/// -Y EXTERNAL -S "cn=ccc,cn=default,ou=pwpolicy,dc=caizhe,dc=org"
New password:
Re-enter new password:
SASL/EXTERNAL authentication started
SASL username: gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth
SASL SSF: 0
Result: Constraint violation (19)
Additional info: Password fails quality checking policy
```

新建用户登录测试密码有效期：

```bash
64c1e4ea conn=1068 fd=14 ACCEPT from IP=192.168.0.131:50662 (IP=0.0.0.0:389)
64c1e4ea conn=1068 op=0 BIND dn="cn=aaa,dc=caizhe,dc=org" method=128
64c1e4ea conn=1068 op=0 BIND dn="cn=aaa,dc=caizhe,dc=org" mech=SIMPLE ssf=0
64c1e4ea ppolicy_bind: Setting warning for password expiry for cn=aaa,dc=caizhe,dc=org = 21 seconds				 #还有21秒过期
64c1e4ea conn=1068 op=0 RESULT tag=97 err=0 text=
64c1e4ea conn=1068 op=1 SRCH base="" scope=0 deref=3 filter="(objectClass=)"
64c1e4ea conn=1068 op=1 SRCH attr=subschemaSubentry
64c1e4ea conn=1068 op=1 SEARCH RESULT tag=101 err=0 nentries=1 text=
64c1e4ea conn=1068 op=2 SRCH base="cn=Subschema" scope=0 deref=3 filter="(objectClass=subschema)"
64c1e4ea conn=1068 op=2 SRCH attr=createTimestamp modifyTimestamp
64c1e4ea conn=1068 op=2 SEARCH RESULT tag=101 err=0 nentries=1 text=
64c1e4ea conn=1068 op=3 SRCH base="" scope=0 deref=0 filter="(objectClass=)"
64c1e4ea conn=1068 op=3 SRCH attr=namingContexts subschemaSubentry supportedLDAPVersion supportedSASLMechanisms supportedExtension supportedControl supportedFeatures vendorName vendorVersion + objectClass
64c1e4ea conn=1068 op=3 SEARCH RESULT tag=101 err=0 nentries=1 text=
64c1e4ea conn=1068 op=4 SRCH base="" scope=0 deref=0 filter="(objectClass=)"
64c1e4ea conn=1068 op=4 SRCH attr=
64c1e4ea conn=1068 op=4 SEARCH RESULT tag=101 err=0 nentries=1 text=
64c1e4ea conn=1068 op=5 SRCH base="cn=Subschema" scope=0 deref=3 filter="(objectClass=)"
64c1e4ea conn=1068 op=5 SRCH attr=hasSubordinates objectClass
64c1e4ea conn=1068 op=5 SEARCH RESULT tag=101 err=0 nentries=1 text=
64c1e4ea conn=1068 op=6 SRCH base="dc=caizhe,dc=org" scope=0 deref=3 filter="(objectClass=)"
64c1e4ea conn=1068 op=6 SRCH attr=hasSubordinates objectClass
64c1e4ea conn=1068 op=6 SEARCH RESULT tag=101 err=32 nentries=0 text=
64c1e4ea conn=1068 op=7 SRCH base="cn=config" scope=0 deref=3 filter="(objectClass=*)"
64c1e4ea conn=1068 op=7 SRCH attr=hasSubordinates objectClass
64c1e4ea conn=1068 op=7 SEARCH RESULT tag=101 err=32 nentries=0 text=
```

注意：原有账户的密码不受影响，只有后面新加的用户会收到密码策略的限制

***

# 自主改密平台

创建一个配置文件

```php 
<?php // My SSP configuration
$keyphrase = "mysecret";
$debug = true;
$use_captcha = false;
$ldap_url = "ldap://192.168.1.250:389";
$ldap_binddn = "CN=admin,DC=innovsharing,DC=com";
$ldap_bindpw = "111111";
$ldap_base = "dc=innovsharing,dc=com";
$ldap_filter = "(&(objectClass=inetOrgPerson)(cn={login}))";
$use_sms = false;
$use_questions = false;

$who_change_password = "user";
$show_extended_error = true;
$pwd_show_policy_pos = "above";
$pwd_show_policy = "always";
#$pwd_no_reuse = true;

#$ldap_use_exop_passwd = true;
#$ldap_use_ppolicy_control = true;
#$pwd_min_lower = 1;
#$pwd_min_upper = 1;
#$pwd_min_digit = 1;
$pwd_min_length = 8;
#$pwd_max_length = 16;
#$hash = "MD5";


## Token
# Use tokens?
# true (default)
# false
$use_tokens = true;
# Crypt tokens?
# true (default)
# false
$crypt_tokens = true;
# Token lifetime in seconds
$token_lifetime = "3600";

## Mail
# LDAP mail attribute
$mail_attributes = array( "mail", "gosaMailAlternateAddress", "proxyAddresses" );
# Get mail address directly from LDAP (only first mail entry)
# and hide mail input field
# default = false
$mail_address_use_ldap = false;
# Who the email should come from
$mail_from = "xxx@innovsharing.com";
$mail_from_name = "Self Service Password";
$mail_signature = "";
# Notify users anytime their password is changed
$notify_on_change = false;
# PHPMailer configuration (see https://github.com/PHPMailer/PHPMailer)
$mail_sendmailpath = '/usr/sbin/sendmail';
$mail_protocol = 'smtp';
$mail_smtp_debug = 0;
$mail_debug_format = 'error_log';
$mail_smtp_host = 'smtp.exmail.qq.com';
$mail_smtp_auth = true;
$mail_smtp_user = 'xxxxx@innovsharing.com';
$mail_smtp_pass = 'xxxxxxxxxxxxx';
$mail_smtp_port = 465;
$mail_smtp_timeout = 30;
$mail_smtp_keepalive = false;
$mail_smtp_secure = 'ssl';
$mail_smtp_autotls = true;
$mail_smtp_options = array();
$mail_contenttype = 'text/plain';
$mail_wordwrap = 0;
$mail_charset = 'utf-8';
$mail_priority = 3;

?>
```
运行新的容器

    docker run -p 9080:80  --restart=always --name selfServicePassword -v $PWD/config.inc.php:/var/www/conf/config.inc.local.php -itd docker.io/ltbproject/self-service-password:1.5

直接修改密码即可(如果忘记密码，可以使用邮箱重置密码)

![](https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/0230802163132.png)

<img src="https://caizhe-img.oss-cn-beijing.aliyuncs.com/blog/ldap/20230728190552.png" style="zoom:50%;" />

## 过期提醒 

SSP 可以改密码很方便，但是有一个弊端：

1、过期之前没有提醒；

2、无法修改已经过期的密码（AD可以，但openldap一直提示密码错误）

编写一个脚本，完成以上功能：

``` bash
LDAP_HOSTURI="ldap://192.168.1.250:389"
LDAP_ROOTDN="cn=admin,dc=innovsharing,dc=com"
LDAP_ROOTPW="111111"
LDAP_SEARCHBASEDN="dc=innovsharing,dc=com"
LDAP_SEARCHFILTER="(&(cn=*)(objectClass=inetOrgPerson))"
LDAP_SEARCHCOMM="ldapsearch -x -H ${LDAP_HOSTURI} -D ${LDAP_ROOTDN} -LLL -w ${LDAP_ROOTPW} ${LDAP_SEARCHFILTER}"
EXPIRE_DAY=165		# ldap 设置了180天过期，提前15天（第165天）发出邮件提醒

${LDAP_SEARCHCOMM} -b ${LDAP_SEARCHBASEDN} dn|awk '{print $2}' > /tmp/1.log

for i in `cat /tmp/1.log`
do
        echo $i
        ModifyTime=`${LDAP_SEARCHCOMM} -b $i +|grep modifyTimestamp|awk '{print $NF}'|cut -c1-8`
        ModifyTime=$(date -d "${ModifyTime}" +%s)
        echo ${ModifyTime}
        NowTime=$(date +%s)
        diff=$(( (NowTime - ModifyTime) / 86400 ))
        echo ${diff}
        if (( ${diff} > ${EXPIRE_DAY ))
        then
           echo "exipire"
           Mail=`${LDAP_SEARCHCOMM} -b $i mail |grep mail|awk '{print $2}'`
           echo "Hi,Please change your password. It will expire." | mail -s "Accont expire warning" ${mail}
        else
           echo "no exipire"
        fi
done
rm -f /tmp/1.log

```

放到定时任务，每天执行一遍

需要安装一些基础命令（mail、gawk、ssmtp）

``` shell
apt install mailutils gawk ssmtp
```

填写邮箱配置

``` shell
vim /etc/ssmtp/ssmtp.conf
root=xxx@innovsharing.com
mailhub=smtp.exmail.qq.com:465
AuthUser=xxx@innovsharing.com
AuthPass=xxxxxxx
UseTLS=Yes
-------------------------
vim /etc/ssmtp/revaliases
root:xxx@innovsharing.com:smtp.exmail.qq.com:465
```

发送邮件确认一下

```bash
 echo "nei rong" | mail -s "zhu ti" xxxxxxx@qq.com
```



***

参考链接：

<https://www.openldap.org/devel/admin/overlays.html>  &#x20;

<https://tutoriels.meddeb.net/openldap-password-policy-managing-users-accounts/>

<https://kifarunix.com/implement-openldap-password-policies/>

<https://tylersguides.com/guides/openldap-password-policy-overlay/>
