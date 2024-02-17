#!/bin/bash

IP_ADDRESS_LOAD_BALANCER=$1

# t=190 # Time in seconds between URLs
t=10
# t=1
n=1 # Number of URLs to load
ratio=1

# URL to generate load for
url="http://$IP_ADDRESS_LOAD_BALANCER/gw/index.php/Mehmed_II."

echo $url