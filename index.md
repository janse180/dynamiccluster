---
layout: home
title: Dynamic Cluster - Dynamically provision worker nodes in the cloud for your cluster
slug: home
permalink: /index.html
---

# Dynamic Cluster

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

Clusters can be configured in many ways based on the requirements, and could range from a small cluster set up and used by a single user, to a large cluster provided as a managed service for many users. An organisation may already manage a cluster on dedicated hardware and want to set up a cluster in the cloud that has a similar configuration, to make it easier for users to use this additional resource.

Dynamic Cluster is therefore designed to be simple and flexible. It can be configured in many ways and can be integrated with different cloud and cluster systems. The system administrator for the cluster can configure it to meet their requirements.

## Get Started

Setting up and managing a cluster requires a reasonable level of understanding of Unix systems administration and the cluster management system. While Dynamic Cluster aims to make it easy to set up a cluster in the cloud, it still requires some understanding of how to use the cloud, and particularly the authentication mechanisms used in the cloud. It is assumed that the system administrator who is setting up and managing the cluster in the cloud has an adequate level of expertise and understanding of Unix, clusters and the cloud.

This software development project just provides information on the Dynamic Cluster software, which is just one component of setting up a cluster in the cloud. Since there are so many different ways that a cluster in the cloud could be set up, we have made a separate project, [Dynamic Cluster as a Service](http://eresearchsa.github.io/dcaas/), which presents some examples on how Dynamic Cluster can be used to deploy a cluster on different infrastructure (all cloud or cloud plus dedicated hardware); different levels of robustness (including high-availability configurations for some of the key components of the cluster such as the head node); as a managed service for multiple users or groups; or as a dedicated cluster for a single user or group. 

We suggest that you start with the [Dynamic Cluster as a Service](http://eresearchsa.github.io/dcaas/) project if you are aiming to set up a cluster. It provides some example reference architectures for different types of clusters, and some tools and documentation for setting up clusters, including Heat templates and deployment scripts.

Some more detailed information about Dynamic Cluster is available below:

* To install Dynamic Cluster and learn how to configure it, see [deployment](./deploy.html).

* To see how to use its web dashboard, see [usage](./usage.html).

* If you want to interactively interface to Dynamic Cluster, either programatically or manually, see [Rest API](./restapi.html).

* If you want to know more about its design, see [design](./design.html).




