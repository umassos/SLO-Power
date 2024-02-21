#!/bin/bash
saved_data_path=$1

manager_file_name="./slo_power_manager.py"

allocated_power_file="allocatedPower"
measured_response_time_file="measuredResponseTimes"
tail_response_time_file="tailResponseTimes"
filtered_response_time_file="filteredResponseTimes"
log_file="logData"
error="errors"
drop="dropRate"
estimated_request="estimatedNumberOfRequests"
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
info_log="infoLog"

extension=".csv"
extension1=".pkl"
extension2=".txt"

sudo python $manager_file_name -asp /gw/ -ts $2 -st $3 -sl $4 -ap ${saved_data_path}${allocated_power_file}${extension} -mrt ${saved_data_path}${measured_response_time_file}${extension} -trt ${saved_data_path}${tail_response_time_file}${extension} -lf ${saved_data_path}${log_file}${extension1} -ev ${saved_data_path}${error}${extension} -dp ${saved_data_path}${drop}${extension} -er ${saved_data_path}${estimated_request}${extension} -ac ${saved_data_path}${allocated_number_of_core_file}${extension} -rac ${saved_data_path}${reactively_allocated_number_of_core_file}${extension} -pac ${saved_data_path}${proactively_allocated_number_of_core_file}${extension} -sp ${saved_data_path}${measured_server_power_file}${extension} -cu ${saved_data_path}${cpu_utilization_file}${extension} -sr ${saved_data_path}${service_rate}${extension} -cf ${saved_data_path}${cpu_frequency_file}${extension} -bfr ${saved_data_path}${best_fit_req_rate}${extension} -bfc ${saved_data_path}${best_fit_cpu_util}${extension} -tbi ${saved_data_path}${to_be_increased_core}${extension} -tbd ${saved_data_path}${to_be_reduced_core}${extension} -il ${saved_data_path}${info_log}${extension2}
