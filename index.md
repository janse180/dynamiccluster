---
layout: home
title: Dynamic Cluster - Dynamically start up and shut down worker nodes in the cloud for your cluster
slug: home
permalink: /index.html
---

<p></p>

  <section id="lead" class="lead">
    Dynamic Cluster is a service running next to your cluster and monitoring its workload, based on which Dynamic Cluster automatically
    starts up and shuts down worker nodes in the cloud.
    
  </section>


## Overview



Dynamic Cluster features a modular design, which makes it easy to be extended to support different types of clusters and cloud systems. 
Current version supports two cluster systems, Torque/MAUI and SGE, as well as two cloud systems, OpenStack and AWS.
More will be added in future releases.



Dynamic Cluster runs independent of the cluster and the cloud. It doesn't store any states in any database.
All states are from the cluster or the cloud. It works according to these states.
Even when Dynamic Cluster is not running, the normal operation of the cluster or the cloud is not affected.
You just lose the ability to automatically grow and shrink your cluster.


## Get Started


To install Dynamic Cluster and learn how to configure it, please see [deployment](./deploy.html).


To see how to use its dashboard, please see [usage](./usage.html).


If you want to interactive Dynamic Cluster, either programatically or manually, please see [Rest API](./restapi.html).



If you want to know more about its design, please see [design](./design.html).


Dynamic Cluster is designed to be simple and flexible. It can be configured in many ways and can be integrated with different systems.
The sysadmin should choose the right components and apply the right policies to your cluster.


This project is purely about Dynamic Cluster. For an example of how it works in a test environment, please see the all in one system in [citc](http://eresearchsa.github.io/citc/).




