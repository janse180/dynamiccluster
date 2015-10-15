---
layout: home
title: Dynamic Cluster - FAQ
slug: faq
permalink: /faq.html
---

# FAQ

Frequently asked questions.

### The cloud is having an outage or having issues firing up instances. What can I do?

Set Auto mode to false in Dashboard's setting view if all resources are not able to grow or shrink.

If one zone is having an outage, and there is a resource (or resources) associated with that zone, you can freeze that resource(s) in Dashboard's resources view.

### How do I delete a worker node?

In Dashboard's resources view, hold the worker node, wait until its state becomes _Held_ and vacate it if it has running jobs. Then remove it.

### Why does MAUI need a restart from time to time?

MAUI needs a restart if this happens: a node, say 1 core, comes up with a particular IP address, e.g. 1.2.3.4, then after some time it is shut down, then some time later another node, say 2 cores, comes up with the same IP 1.2.3.4. From MAUI's perspective, the two nodes are the same because they have the same IP address, but actually they are not, the first one has 1 core and the second one has 2 cores. The consequence is that in MAUI, node 1.2.3.4 always has 1 core because that information will not be updated once the node appears in MAUI. A MAUI restart will update this information so that MAUI knows 1.2.3.4 has 2 cores now, and can distribute jobs properly.

This is done by a cronjob which checks MAUI to see if there is inconsistent information. If yes the cronjob will restart MAUI.
