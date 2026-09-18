---
title: About
description: Notes on Linux, Kubernetes, and cloud-native infrastructure
date: '2019-02-28'
aliases:
  - about-us
  - about-hugo
  - contact
license: CC BY-NC-ND
lastmod: '2026-09-18'
menu:
    main: 
        weight: -90
        params:
            icon: user
---

Welcome — this is my notebook on Linux, Kubernetes, and cloud-native infrastructure.

Most of what you will find here started life as a runbook for a problem I had to solve at work: standing up an OpenLDAP directory, building a highly-available Kubernetes cluster, tuning Nginx, or debugging a redirect rule at 2 a.m. The posts are written to be useful to my future self first — concrete commands, real config files, and the reasoning behind each decision.

> The path is simple; keep it real and keep it short.

A few things I care about:

- **Reproducible steps.** Every guide should get you from a bare machine to a working result, including the parts that bit me.
- **Alternatives, not dogma.** Where there is a trade-off — RDB vs AOF, raw vs qcow2, Docker vs KVM — I try to say what it costs.
- **Honest writing.** Notes are corrections of earlier mistakes, so corrections to these notes are always welcome.

If something here saved you time, or if you spot an error, the source lives on [GitHub](https://github.com/ITzhe/blog) — open an issue or send a pull request.
