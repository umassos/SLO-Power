#!/bin/bash

# httpmon accepts changing some of the command-line parameters at run-time,
# by accepting commands through stdin. This is an example script that automates
# dynamic workload generation using httpmon. httpmon's output is redirected to
# httpmon.log.

#
# Experiment parameters
#

IP_ADDRESS_LOAD_BALANCER=$1

# t=190 # Time in seconds between URLs
t=10
# t=1
n=1 # Number of URLs to load
ratio=1

# URL to generate load for
url="http://$IP_ADDRESS_LOAD_BALANCER/gw/index.php/Mehmed_II."

urlfile="./link.out"
concurrencyfile=$2
# concurrencyfile="./wikipedia_cluster_1_short.out"
# concurrencyfile="./eval_workload7.out"
# concurrencyfile="./azure_trace_slice3_100_240_cluster.out"
# concurrencyfile="./azure_trace_slice3_1_100_240_cluster.out"

FIFO_FILE=httpmon.fifo
# version="feb16-1.log"
version=$3
FIFO_LOG=httpmon-$version

#
# Useful functions
#
function readline {
        echo $url/`sed "$1q;d" $urlfile`
}
function readlineANDcolumn {
        echo `awk '(NR==$1){print $1}' $concurrencyfile`
}

#
# Experiment verbs (see below for usage)
#
function setStart {
        echo [`date +%s`] start
}
function setCount {
        echo [`date +%s`] count=$1
        echo "count=$1" >&9
}
function setOpen {
        echo [`date +%s`] open=$1
        echo "open=$1" >&9
}
function setThinkTime {
        echo [`date +%s`] thinktime=$1
        echo "thinktime=$1" >&9
}
function setConcurrency {
        echo [`date +%s`] concurrency=$1
        echo "concurrency=$1" >&9
}
function setTimeout {
        echo [`date +%s`] timeout=$1
        echo "timeout=$1" >&9
}
function setUrl {
        echo [`date +%s`] url=$1
        echo "url=$1" >&9
}
function setStop {
        setConcurrency 0
        echo [`date +%s`] stop
}
function httpmonKill {
        echo [`date +%s`] httpmonkill
        for x in `ps aux | grep httpmon | awk '{print $2}'`; do kill $x; done
}
#
# Initialization
#

# Create FIFO to communicate with httpmon and start httpmon
rm -f $FIFO_FILE
mkfifo $FIFO_FILE

/workspace/httpmon/httpmon --url $url --concurrency 0 --dump --open < $FIFO_FILE &> $FIFO_LOG &
exec 9> $FIFO_FILE

#
# Initialize experiment
#
setOpen 1
setThinkTime 1

#
# Run experiment
#
LINE=1
setStart

while read -r my_line
do
    newurl=$url
    concur_per_sec=$my_line

    setConcurrency $concur_per_sec
    setUrl $newurl
    sleep $t
done < $concurrencyfile

echo "Finishing..."
setStop
httpmonKill
mv httpmon-dump.csv httpmon-dump-$version.csv