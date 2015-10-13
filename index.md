---
layout: home
title: Dynamic Cluster - Dynamically provision worker nodes in the cloud for your cluster
slug: home
permalink: /index.html
---

<p></p>

  <section id="lead" class="lead">

      Dynamic Cluster can dynamically provision cluster worker nodes in the cloud, automatically scaling the size of the cluster to meet the workload. 
    
  </section>


## Overview

Dynamic Cluster is a service that runs alongside your cluster management system and monitors its workload, based on which it automatically starts up and shuts down worker nodes in the cloud. It takes advantage of the scalability and elasticity of the cloud to ensure that the cloud resources automatically match the cluster workload, within a specified maximum and minimum cluster size.

Dynamic Cluster features a modular design, which allows it to be easily extended to support different types of clusters and cloud infrastructure. 
Version 1 supports two cluster management systems, Torque/MAUI and SGE, as well as two cloud systems, OpenStack and AWS.
More will be added in future releases.

Dynamic Cluster runs independently of the cluster and the cloud. It doesn't store any states in any database.
All state information is obtained from the cluster and the cloud, and it works according to these states.
Even when Dynamic Cluster is not running, the normal operation of the cluster or the cloud is not affected, 
you just lose the ability to automatically grow and shrink your cluster.


## Get Started

Dynamic Cluster is designed to be simple and flexible. It can be configured in many ways and can be integrated with different cloud and cluster systems.
The system administrator for the cluster should choose the right components and apply the right policies for your cluster. 

The [Dynamic Cluster as a Service](http://eresearchsa.github.io/dcaas/) project presents some examples on how Dynamic Cluster can be used to deploy a cluster on different infrastructure (all cloud or cloud plus dedicated hardware); different levels of robustness, including high-availability configurations for some of the key components of the cluster such as the head node; as a managed service; or as a dedicated cluster for a single user or group.  

* To install Dynamic Cluster and learn how to configure it, see [deployment](./deploy.html).

* To see how to use its web dashboard, see [usage](./usage.html).

* If you want to interactively interface to Dynamic Cluster, either programatically or manually, see [Rest API](./restapi.html).

* If you want to know more about its design, see [design](./design.html).




