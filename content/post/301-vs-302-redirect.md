---
title: "301 vs 302: What's the Difference"
date: 2016-12-11T10:59:21+08:00
draft: false
slug: "301-vs-302-redirect"
tags: ["HTTP", "SEO"]
---

1) The difference between 301 and 302.

Both the 301 and 302 status codes mean "redirect". That is, after the browser receives this status code from the server, it automatically jumps to a new URL, which it reads from the `Location` header of the response. From the user's point of view, the address A they typed instantly becomes another address B — that much is shared by both codes.

The difference is this: a 301 means the resource at the old address A has been permanently removed (it is no longer reachable). While a search engine crawls the new content, it also swaps the old URL out for the redirected one.

A 302 means the resource at the old address A is still there (still accessible) and the redirect is only a temporary jump from address A to address B. The search engine crawls the new content but keeps the old URL indexed.

2) Why redirect at all?

1. Site restructuring (for example, changing the page directory layout);
2. A page has been moved to a new address;
3. The page's file extension changed (an application needs to rename `.php` to `.html` or `.shtml`).

In case 3, without a redirect the old address in a user's bookmarks or in a search engine's database can only return a 404, and the traffic is simply lost. Sites that have registered several domain names also need redirects so that visitors to those domains are sent automatically to the main site.
