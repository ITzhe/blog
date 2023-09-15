---
title: "Clamv"
date: 2018-03-13T10:59:21+08:00
draft: false
tags: ["安全"]
---

最近研究安全方向，发现Linux下的一些杀毒软件比较少，今天给大家介绍一款开源的轻量级杀毒软件clamAV。

**特点**

   1）GNU开源软件

　　2）快速扫描

　　3）可以检测35000种病毒，蠕早，特洛依，包括Microsoft Office文档及宏病毒

　　4）能够检测压缩文件（Zip RAR Tar Gzip Bzip2……）

　　5）强大的邮件扫描功能

　　6）扩展性强

1.时间同步

	ntpdate time1.aliyun.com

2.安装clamAV。（可以使用阿里云的epel源）

	yum install clamav

3.更新病毒库。（第一次下载可能会花点儿时间）

	 freshclam

4.测试：下载带病毒软件

	wget http://www.eicar.org/download/eicar_com.zip

4.使用 clamscan 开始扫描

	clamscan -r /etc/
	
	…………
	./.rnd: OK
	/eicar_com.zip: Eicar-Test-Signature FOUND
	./.cshrc: OK
	…………

		----------- SCAN SUMMARY -----------
	Known viruses: 5748467
	Engine version: 0.99.2
	Scanned directories: 1
	Scanned files: 15
	Infected files: 1
	Data scanned: 0.10 MB
	Data read: 91.95 MB (ratio 0.00:1)
	Time: 19.179 sec (0 m 19 s)

可以加上 --remove 参数，扫描完之后直接杀掉病毒

可以加上定时任务每天定时扫描和更新病毒库,此处不再介绍



如果你发现了ClamVA查杀不了的病毒，可以在以下的网址提交相关的信息

      http://www.clamav.net/sendvirus.html 

官方网址：

	  http://www.clamav.net/lang/en/
	  http://www.clamav.net/sendvirus.html