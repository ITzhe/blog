---
title: "Gitlab大文件清理"
date: 2023-03-01T17:44:11+08:00
draft: false
tags: ["git"] 
---

1、首先需要关闭远程仓库的分支保护，允许强制推送：  
"Settings" -> "Repository" -> scroll down to "Protected branches".

2、克隆项目,拉取所有分支：
``` 
git clone xxx # 默认拉取master分支
cd xx #进入拉取的文件夹
git branch -r | grep -v '\->' | while read remote; do git branch --track "${remote#origin/}" "$remote"; done
git fetch --all
git pull --all
```

3、查找大文件（将最大的10个文件查询下来）

``` shell
git rev-list --objects --all | grep "$(git verify-pack -v .git/objects/pack/*.idx | sort -k 3 -n | tail -10 | awk '{print$1}')"
```

4、清理查找的大文件（一次只能处理一个文件/文件夹）：
``` shell
git filter-branch --force --index-filter 'git rm -rf --cached --ignore-unmatch 目录/文件' --prune-empty --tag-name-filter cat -- --all
```

5、删除并回收空间

``` shell
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now
git gc --aggressive --prune=now
```

6、推送远程仓库：
``` shell
git push origin --force --all
git remote prune origin
```

然后其他人重新克隆项目即可

---
参考链接：https://www.msnao.com/2021/06/15/5031.html