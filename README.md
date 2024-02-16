The aim of this page is to provide steps and codes to reproduce the results for the following paper:

> M. Savasci, et al., "SLO-Power: SLO and Power-aware Elastic Scaling for Web Services," in 2024 IEEE/ACM 24rd International Symposium on Cluster, Cloud and Internet Computing (CCGrid), Philadelphia, USA, 2024.

Below, we describe in detail:

* the configuration of the physical server we used for experiments,
* the experiments we have performed.

# Configuration of Physical Servers
We run Ubuntu Ubuntu 20.04 LTS on our physical servers. The configuration described below was tested only for that particular version of operating system.

## Application
For our experiments, we used German Mediawiki with Memcached. You can download image from [here](https://drive.google.com/file/d/1nZ0pMFGASFhaA4tthHhLlgdFP-RGt5tH/view?usp=drive_link):

Alternatively, you can download it using the following `gdown` command:

`gdown 1nZ0pMFGASFhaA4tthHhLlgdFP-RGt5tH`

For installation details of gdown, please see [gdown GitHub repo](https://github.com/wkentaro/gdown?source=post_page-----ad9985a04ed9--------------------------------).

After you download the container image tarball, you need to restore and create a container from it. To do this, run the following commands:

P.S. Before running above commands, you need to make sure that you run `lxd init` for initialization purpose.

`lxc image import mediawiki_german_with_memcached.tar.gz --alias image-name`

`lxc launch image-name container-name`


https://drive.google.com/file/d/1nZ0pMFGASFhaA4tthHhLlgdFP-RGt5tH/view?usp=sharing

[![DOI](https://zenodo.org/badge/758160062.svg)](https://zenodo.org/doi/10.5281/zenodo.10672465)