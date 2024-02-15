#!/bin/bash
python_venv_path="/workspace1/PoVerScaler_venv/bin/python" 

script_folder_path="/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/"
saved_data_path="/nfs/obelix/raid2/msavasci/SLO-Power-Experiments/SLO-Power/Experiment-423/"

manager_file_name="manager_server_with_policy15_cluster_without_cpu_util_v2.py"

allocated_power_file="allocatedPower"
estimated_power_file="estimatedPower"
measured_response_time_file="measuredResponseTimes"
tail_response_time_file="tailResponseTimes"
filtered_response_time_file="filteredResponseTimes"
log_file="logData"
error="errors"
drop="dropRate"
estimated_request="estimatedNumberOfRequests"
pterm="pTerms"
iterm="iTerms"
operation_point="operatingPointValues"
integrator="integrators"
integrator_switch="integratorSwitch"
allocated_number_of_core_file="allocatedNumberOfCores"
reactively_allocated_number_of_core_file="reactiveNumberOfCores"
proactively_allocated_number_of_core_file="proactiveNumberOfCores"
measured_server_power_file="serverPower"
cpu_utilization_file="cpuUtil"
service_rate="serviceRate"
cpu_frequency_file="cpuFreq"
best_fit_req_rate="bestFitReqRate"
best_fit_cpu_util="bestFitCpuUtil"
to_be_increased_core="toBeIncreasedCoreInfo"
to_be_reduced_core="toBeDecreasedCoreInfo"

tuning_percentage="-1-t"
extension=".csv"
extension1=".pkl"

sudo $python_venv_path ${script_folder_path}${manager_file_name} -ap ${saved_data_path}${allocated_power_file}${tuning_percentage}${extension} -ep ${saved_data_path}${estimated_power_file}${tuning_percentage}${extension} -rt ${saved_data_path}${measured_response_time_file}${tuning_percentage}${extension} -trt ${saved_data_path}${tail_response_time_file}${tuning_percentage}${extension} -frt ${saved_data_path}${filtered_response_time_file}${tuning_percentage}${extension} -lf ${saved_data_path}${log_file}${tuning_percentage}${extension1} -ev ${saved_data_path}${error}${tuning_percentage}${extension} -dp ${saved_data_path}${drop}${tuning_percentage}${extension} -er ${saved_data_path}${estimated_request}${tuning_percentage}${extension} -pt ${saved_data_path}${pterm}${tuning_percentage}${extension} -it ${saved_data_path}${iterm}${tuning_percentage}${extension} -op ${saved_data_path}${operation_point}${tuning_percentage}${extension} -in ${saved_data_path}${integrator}${tuning_percentage}${extension} -is ${saved_data_path}${integrator_switch}${tuning_percentage}${extension} -ac ${saved_data_path}${allocated_number_of_core_file}${tuning_percentage}${extension} -rac ${saved_data_path}${reactively_allocated_number_of_core_file}${tuning_percentage}${extension} -pac ${saved_data_path}${proactively_allocated_number_of_core_file}${tuning_percentage}${extension} -sp ${saved_data_path}${measured_server_power_file}${tuning_percentage}${extension} -cu ${saved_data_path}${cpu_utilization_file}${tuning_percentage}${extension} -sr ${saved_data_path}${service_rate}${tuning_percentage}${extension} -cf ${saved_data_path}${cpu_frequency_file}${tuning_percentage}${extension} -bfr ${saved_data_path}${best_fit_req_rate}${tuning_percentage}${extension} -bfc ${saved_data_path}${best_fit_cpu_util}${tuning_percentage}${extension} -tbi ${saved_data_path}${to_be_increased_core}${tuning_percentage}${extension} -tbd ${saved_data_path}${to_be_reduced_core}${tuning_percentage}${extension}
