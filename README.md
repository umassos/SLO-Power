The aim of this page is to provide steps and codes to reproduce the results for the following paper:

> M. Savasci, et al., "SLO-Power: SLO and Power-aware Elastic Scaling for Web Services," in 2024 IEEE/ACM 24rd International Symposium on Cluster, Cloud and Internet Computing (CCGrid), Philadelphia, USA, 2024.

Below, we describe in detail:

* the configuration of the physical server we used for experiments,
* the SLO-Power implementation.

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

We suggest you to create a Python virtual environment and install modules inside of this virtual environment. To install from `requirements.txt`, run the following command:

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

We provide a `json` file to let SLO-Power manager to know the machines in the cluster. For this purpose, please see and update [cluster_machines.json or single_machine.json](./src/cluster_machines.json) file.



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

After haproxy is installed, its configuration file located at `/etc/haproxy/haproxy.cfg` needs to be edited. For convenience, we provied this configuration file as [haproxy.cfg](./haproxy.cfg). In this file, parameters of `CONTAINER_NAME`, `IP_ADDRESS_OF_MACHINE_HOSTING_CONTAINER`, and `PORT_NUMBER_OF_CONTAINER` must be provided. Here, `CONTAINER_NAME` is the container we created earlier which host Mediawiki application. In addition, `PORT_NUMBER_OF_CONTAINER` must be same as the one when creating the proxy for the container.

We initialized above parameters with some values in this image. Therefore, you need to set them with correct values.

We also provide HAProxy LXC image for your convenience. It can be downloaded from [here](https://drive.google.com/file/d/1KtDZeMU-2enfnRhV5l147G-VW8CjHJHE/view?usp=drive_link)

Alternatively, you can download it using the following `gdown` command:

`gdown 1KtDZeMU-2enfnRhV5l147G-VW8CjHJHE`

After you download the container image tarball, you need to restore and create a container from it. To do this, run the following commands:

`lxc image import haproxy_container.tar.gz --alias {IMAGE_NAME}`

`lxc launch {IMAGE_NAME} {CONTAINER_NAME}`

## Workload Generator
Workload generator is provided in [workload-generator](./workload-generator/) directory. Our workload generator is based on httpmon workload generator. For installation details, please see [here](https://github.com/cloud-control/httpmon). Usage of workload generator is as follows:
```
./generator $1 $2 $3 $4 where

$1 --> path to the binary of the httpmon

$2 --> IP address of HAProxy server (Listening port number can be provided as `IP_address:port_number`)

$3 --> workload trace file

$4 --> version of the workload generator's output that is logged
```

For example, the following command 

`./generator.sh /workspace/httpmon 192.168.245.55 /SLO-Power/workload-traces/scaled_wikipedia_traces.out v1`

initiates a httpmon workload generator, using binary located at `/workspace` directory, using traces of `single_node_level_scaled_wikipedia_traces.out`, sending requests to HAProxy hosting on IP of `192.168.245.55`, and saving workload generator output with `v1` postfix. By default, the workload generator output is saved under `/tmp/` directory.

## Workload Traces
We used two real workload traces: wikipedia and Azure traces. We scaled both wikipedia and Azure traces considering our cluster size. For wikipedia, we scaled traces between 60 and 240, while we scaled between 100 and 240 for Azure traces. All these traces are under [workload-traces](./workload-traces/) directory. In addition to the cluster level workload traces, we provided single node level workload traces in the same folder as well. You should pick them accordingly based on your setup.

## Running SLO-Power
The source codes of SLO-Power is located under [src](./src/) directory. In the following, we will show how to run SLO-Power.

### 1. Running SLO-Agent parts
Our SLO-Agent has two modules: power capper and core allocator. 

#### 1.a. Running power capper module (run with `sudo`)
```
usage: power_capper_server.py [-h] [-p PORT] [-w WORKERS] [-e POWER]

Power Capping Server

optional arguments:

  -h, --help            show this help message and exit

  -p PORT, --port PORT  Network port (default: 8088)

  -w WORKERS, --workers WORKERS
                        Max Number of workers (default: 10)
                        
  -e POWER, --power POWER
                        Default power (default: 85000000)
```

#### 1.b. Running core allocator module
```
usage: dynamic_core_allocator.py [-h] [-H HOST] [-p PORT] [-w WORKERS] [-d DOMAIN] [-c CORES]

Dynamic Core Allocator

optional arguments:
  -h, --help            show this help message and exit

  -H HOST, --host HOST  Network host (default: 0.0.0.0)

  -p PORT, --port PORT  Network port (default: 8090)

  -w WORKERS, --workers WORKERS
                        Max number of workers (default: 10)

  -d DOMAIN, --domain DOMAIN
                        Default container (default: mediawiki-51-1)

  -c CORES, --cores CORES
                        Default number of cores (default: 16)
```

We also developed two services to provide power measurement via Intel RAPL interface and container information such as its CPU utilization measurement. These two services can be run as follows.

### 2. Running RAPL power measurement service (run with `sudo`)
```
usage: rapl_power_monitor_server.py [-h] [-p PORT] [-w WORKERS]

Container Service Server

optional arguments:
  -h, --help            show this help message and exit

  -p PORT, --port PORT  Network port (default: 8091)
  
  -w WORKERS, --workers WORKERS
                        Max Number of workers (default: 10)
```

### 3. Running container service
```
usage: container_service_server.py [-h] [-H HOST] [-p PORT] [-w WORKERS]

Container Service Server

optional arguments:
  -h, --help            show this help message and exit

  -H HOST, --host HOST  Network host (default: 0.0.0.0)

  -p PORT, --port PORT  Network port (default: 8089)

  -w WORKERS, --workers WORKERS
                        Max Number of workers (default: 10)
```

**Warning:** Before running the SLO-Power Manager, make sure that application is warmed up by sending requests from the workload generator. For example, the following command

```/workspace/httpmon --url http://192.168.245.55/gw/index.php/Mehmed_II. --concurrency 40 --thinktime 1 --open```

initiates a httpmon workload generator, using binary located at `/workspace` directory, sending requests to HAProxy hosting on IP of `192.168.245.55` with application path of `gw/index.php/`, and requesting `Mehmed_II.` page `40 times per second`. More details of this command can be found [here](https://github.com/cloud-control/httpmon). 

### 4. Running SLO-Power Manager
We provide a [bash script](./src/run_slo_power_manager.sh) to run slo-power manager Python file. Usage of the script is as follows:

```
./run_slo_power_manager $1 $2 $3 $4 where

$1 --> filepath where experiment files are saved to

$2 --> target SLO (in terms of ms)

$3 --> time granularity that SLO-Power works (1s in our experiments)

$4 --> filepath where HAProxy log file is (Default is /var/log/haproxy.log)
```

In the `run_slo_power_manager`, you might need to change `python` command at line 31 based on your setup. For example, if your `python` call is as `python3`, then replace `python` with `python3`.

For instance, the following command

`./run_slo_power_manager.sh artifact_eval/test2/ 250 1 /var/log/haproxy.log`

initiates an experiment, saving the outcomes in the directory `artifact_eval/test2/`, while configuring the target to be `250`ms with results at a granularity of `1`s.
A sample output would produce:

```
Min core: 2, Max core: 16
Current core info of containers: {('192.168.245.51', 'mediawiki-51-1'): 3}
Controller max power limit for node: {('192.168.245.51', 'mediawiki-51-1'): 55}
Target response time of the application: 250 ms
Ref_input: 250
slo_guard: 0.8
Guarded SLO target: 200.0
HAProxy log file is cleared for the initialization purpose.
Initial resource calibration is in progress...
Arrival rate: 41, service rate: 9, expected response time: 0.2 s
Proactive estimated number of core is 11.
Proactively estimated number of core for cluster: 11
{('192.168.245.51', 'mediawiki-51-1'): 0.06}
{('192.168.245.51', 'mediawiki-51-1'): 11}
11 core(s) has been allocated to mediawiki-51-1 hosted on 192.168.245.51.
Power has been set to 77 Watts on 192.168.245.51 due to change in number of core by the proactive scaler.
Initial resource calibration is done :)
Iteration: 1, Estimated number of request: 41, Average response time: 125.66666666666667, Tail response time: 140.9
Proactively scaling up decision is gonna be taken...
To be increased # cores: 0
12 core(s) has been allocated to mediawiki-51-1 hosted on 192.168.245.51.
Power is being set to 80 Watts (increase)
Power has been set to 80 Watts on 192.168.245.51 (Due to inner power scaler loop).
```

We provide two configuration files which are required to set if the experiment runs at the single machine level or cluster level. These configuration files are [single_machine.json](./src/single_machine.json) and [cluster_machines.json](./src/cluster_machines.json). These files should be modified based on your own setup. We hardcoded this configuration file in [slo_power_manager.py](./src/slo_power_manager.py) at line 28 as `machines_config_file = "./single_machine.json"`. This line should be updated with the configuration file that is based on your setup.

In addition, SLO-Power has parameters to set up. This parameters can be set up at [config](./src/power_manager_config.json) file. From this configuration file, a few parameters are specific to setup (single machine level or cluster level). These parameters are given below and should be set accordingly.

```cluster_size``` is to mention how many machines are used in the experiment (total number of machines mentioned in `single_machine.json`, i.e., 1 or in `cluster_machines.json`)

```service_rate``` keeps service rate of the application under the setup.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10673278.svg)](https://doi.org/10.5281/zenodo.10673278)
