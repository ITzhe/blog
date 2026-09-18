---
title: "ClamAV on Linux"
date: 2018-03-13T10:59:21+08:00
draft: false
slug: "clamav"
tags: ["Security"]
---

I have been looking into security lately and noticed there are not many antivirus options on Linux. Today I want to introduce ClamAV, an open-source lightweight antivirus engine.

**Features**

1. GNU open-source software

2. Fast scanning

3. Detects 35,000 kinds of viruses, worms, and Trojans, including Microsoft Office documents and macro viruses

4. Can scan inside archives (Zip, RAR, Tar, Gzip, Bzip2, ...)

5. Strong email scanning

6. Highly extensible

1. Sync the time:

	ntpdate time1.aliyun.com

2. Install ClamAV (you can use the Aliyun EPEL repo):

	yum install clamav

3. Update the virus database (the first download takes a while):

	 freshclam

4. Test it by downloading a known-bad file:

	wget http://www.eicar.org/download/eicar_com.zip

4. Scan with `clamscan`:

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

You can add the `--remove` flag to delete the infected files as soon as the scan finds them.

You can also add a cron job to scan and update the virus database on a schedule — I will not go into that here.

If you find a virus that ClamAV cannot detect, you can submit the sample at:

      http://www.clamav.net/sendvirus.html

Official site:

	  http://www.clamav.net/lang/en/
	  http://www.clamav.net/sendvirus.html
