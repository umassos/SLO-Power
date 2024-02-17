#!/bin/bash
python_venv_path="/workspace1/PoVerScaler_venv/bin/python" 

script_folder_path="/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/"
saved_data_path="/nfs/obelix/raid2/msavasci/SLO-Power-Experiments/SLO-Power/Experiment-310/"

manager_file_name="manager_naive_vertical_scaler_cluster.py"

measured_response_time_file="measuredResponseTimes"
tail_response_time_file="tailResponseTimes"
drop="dropRate"
estimated_request="estimatedNumberOfRequests"
measured_server_power_file="serverPower"
cpu_utilization_file="cpuUtil"
cpu_frequency_file="cpuFreq"
number_of_core_file="allocatedNumberOfCores"
log_data_file="logData"

tuning_percentage="-1-t"
extension=".csv"
extension1=".pkl"

sudo $python_venv_path ${script_folder_path}${manager_file_name} -rt ${saved_data_path}${measured_response_time_file}${tuning_percentage}${extension} -trt ${saved_data_path}${tail_response_time_file}${tuning_percentage}${extension} -dp ${saved_data_path}${drop}${tuning_percentage}${extension} -er ${saved_data_path}${estimated_request}${tuning_percentage}${extension} -sp ${saved_data_path}${measured_server_power_file}${tuning_percentage}${extension} -cu ${saved_data_path}${cpu_utilization_file}${tuning_percentage}${extension} -cf ${saved_data_path}${cpu_frequency_file}${tuning_percentage}${extension} -nc ${saved_data_path}${number_of_core_file}${tuning_percentage}${extension} -ld ${saved_data_path}${log_data_file}${tuning_percentage}${extension1} -l /var/log/haproxy.log -s 2
