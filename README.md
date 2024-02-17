The aim of this page is to provide steps and codes to reproduce the results for the following paper:

> M. Savasci, et al., "SLO-Power: SLO and Power-aware Elastic Scaling for Web Services," in 2024 IEEE/ACM 24rd International Symposium on Cluster, Cloud and Internet Computing (CCGrid), Philadelphia, USA, 2024.

Below, we describe in detail:

* the configuration of the physical server we used for experiments,
* the experiments we have performed.

# Configuration of Physical Servers
We run Ubuntu Ubuntu 20.04 LTS on our physical servers. The configuration described below was tested only for that particular version of operating system.

## Python installation
We used Python version 3.8.10 in our setup. Therefore, we suggest you to use same version.

### Python modules
SLO-Power requires the following Python modules:
* grpc
* numpy
* rapl

We generated [requirement.txt](src/requirements.txt) for required Python modules except rapl module because it is external module obtained from [here](https://github.com/wkatsak/py-rapl).

We suggest you to create a Python virtual environment and install modules inside of this virtual environment. To install from requirements.txt, run the following command:

`pip install -r /path/to/requirements.txt`

To install rapl module, clone the repo first

'git clone https://github.com/wkatsak/py-rapl.git`

Then, go to the inside of the directory and run

`pip install .`

This command will use `setup.py` to install rapl module.

## LXD installation
We used LXD version 5.19 for clustering and therefore application deployment. LXD can be installed using snap package manager. To install it,

`sudo snap install lxd --channel=5.19/stable`

If you already have LXD in your machine, you can switch to version 5.19 using the following command

`sudo snap refresh lxd --channel=5.19/stable`

## Application
For our experiments, we used German Mediawiki with Memcached. You can download image from [here](https://drive.google.com/file/d/1nZ0pMFGASFhaA4tthHhLlgdFP-RGt5tH/view?usp=drive_link):

Alternatively, you can download it using the following `gdown` command:

`gdown 1nZ0pMFGASFhaA4tthHhLlgdFP-RGt5tH`

For installation details of `gdown`, please see [gdown GitHub repo](https://github.com/wkentaro/gdown?source=post_page-----ad9985a04ed9--------------------------------).

After you download the container image tarball, you need to restore and create a container from it. To do this, run the following commands:

P.S. Before running above commands, you need to make sure that you run `lxd init` for initialization purpose.

`lxc image import mediawiki_german_with_memcached.tar.gz --alias {IMAGE_NAME}`

`lxc launch {IMAGE_NAME} {CONTAINER_NAME}`

To see if the container is up, please run

`lxc list`

commmand and make sure container runs.

In addition to above steps, we add a proxy to container to receive requests from the HAProxy. We basically do port forwarding here.

To add a proxy, please run the following command.

`lxc config device add {CONTAINER_NAME} {PROXY_NAME} proxy listen=tcp:0.0.0.0:{PORT_NUMBER} connect=tcp:127.0.0.1:80`

## HAProxy
We use HAProxy v2.7.10 in front of backend servers for load balancing. You need to install HAProxy first. It can be installed

`sudo apt install haproxy=2.7.10-1ppa1~bionic`

To verify it is installed, execute:

`haproxy -v`

This command should display the version number of the installed HAProxy.

After haproxy is installed, its configuration file located at `/etc/haproxy/haproxy.cfg` needs to be edited. For convenience, we provied this configuration file as [haproxy.cfg](./haproxy.cfg). In this file, parameters of CONTAINER_NAME, IP_ADDRESS_OF_MACHINE_HOSTING_CONTAINER, and PORT_NUMBER_OF_CONTAINER must be provided. Here, CONTAINER_NAME is the container we created earlier which host Mediawiki application. In addition, PORT_NUMBER_OF_CONTAINER must be same as the one when creating the proxy for the container.

We also provide HAProxy LXC image for your convenience. It can be downloaded from [here]()

Alternatively, you can download it using the following `gdown` command:

`gdown `

We initialized above parameters with some values in this image. Therefore, you need to set them with correct values.

## Workload Generator
Workload generator is provided in [workload-generator](./workload-generator/) directory. Our workload generator is based on httpmon workload generator. For installation details, please see [here](https://github.com/cloud-control/httpmon). Usage of workload generator is as follows:

`./generator $1 $2 $3` where

$1 --> IP address of HAProxy server

$2 --> workload trace file

$3 --> name of the file that workload generator's output is logged

## Workload Traces
We used two real workload traces: wikipedia and Azure traces. We scaled both wikipedia and Azure traces considering our cluster size. For wikipedia, we scaled traces between 60 and 240, while we scaled between 100 and 240 for Azure traces. All these traces are under [workload-traces](./workload-traces/) directory.

[![DOI](https://zenodo.org/badge/758160062.svg)](https://zenodo.org/doi/10.5281/zenodo.10672465)