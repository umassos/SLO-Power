#!/bin/bash
python_venv_path="/workspace1/PoVerScaler_venv/bin/python" 

script_folder_path="/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/"
saved_data_path="/nfs/obelix/raid2/msavasci/SLO-Power-Experiments/SLO-Power/Experiment-422/"

manager_file_name="pegasus_manager_server.py"

allocated_power_file="allocatedPower"
measured_response_time_file="measuredResponseTimes"
tail_response_time_file="tailResponseTimes"
log_file="logData"
error="errors"
drop="dropRate"
estimated_request="estimatedNumberOfRequests"
measured_server_power_file="serverPower"
cpu_utilization_file="cpuUtil"
cpu_frequency_file="cpuFreq"

extension=".csv"
extension1=".pkl"

sudo $python_venv_path ${script_folder_path}${manager_file_name} -ap ${saved_data_path}${allocated_power_file}${extension} -rt ${saved_data_path}${measured_response_time_file}${extension} -trt ${saved_data_path}${tail_response_time_file}${extension} -lf ${saved_data_path}${log_file}${extension1} -ev ${saved_data_path}${error}${extension} -dp ${saved_data_path}${drop}${extension} -er ${saved_data_path}${estimated_request}${extension} -sp ${saved_data_path}${measured_server_power_file}${extension} -cu ${saved_data_path}${cpu_utilization_file}${extension} -cf ${saved_data_path}${cpu_frequency_file}${extension}
