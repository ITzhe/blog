---
title: "Purging Large Files from a GitLab Repository"
date: 2023-03-01T17:44:11+08:00
draft: false
slug: "gitlab-purge-large-files"
tags: ["git"]
---

1. First, disable branch protection on the remote repository so force pushes are allowed: "Settings" -> "Repository" -> scroll down to "Protected branches".

2. Clone the project and fetch every branch:

``` 
git clone xxx # pulls the master branch by default
cd xx # enter the cloned directory
git branch -r | grep -v '\->' | while read remote; do git branch --track "${remote#origin/}" "$remote"; done
git fetch --all
git pull --all
```

3. Find the large files (list the 10 largest):

``` shell
git rev-list --objects --all | grep "$(git verify-pack -v .git/objects/pack/*.idx | sort -k 3 -n | tail -10 | awk '{print$1}')"
```

4. Purge the large files you found (one file or directory at a time):

``` shell
git filter-branch --force --index-filter 'git rm -rf --cached --ignore-unmatch path/to/file' --prune-empty --tag-name-filter cat -- --all
```

5. Delete and reclaim the space:

``` shell
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now
git gc --aggressive --prune=now
```

6. Push to the remote repository:

``` shell
git push origin --force --all
git remote prune origin
```

Everyone else can then re-clone the project.

---
Reference: https://www.msnao.com/2021/06/15/5031.html
