import grpc
from Utility import Utility
import container_service_pb2 as pb2_container_service
import container_service_pb2_grpc as pb2_container_service_grpc
import rapl_power_monitor_pb2 as pb2_monitor
import rapl_power_monitor_pb2_grpc as pb2_monitor_grpc
import dynamic_core_allocator_pb2 as pb2_core_allocator
import dynamic_core_allocator_pb2_grpc as pb2_core_allocator_grpc
import argparse
import time
import timeit
import statistics as stat
import math
import subprocess
import pickle
import json
import os
import numpy as np

f_real_rt, f_tail_rt, f_drop_percent, f_est_number_of_request, f_measured_server_power, f_allocated_number_of_cores, f_cpu_util, f_cpu_freq, f_log_data = "", "", "", "", "", "", "", "", ""

# Instantiate Utility class to use utilities such as 'converting from second to millisecond', etc.
my_utility = Utility()

machines_config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/cluster_machines.json"
config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/power_manager_config.json"
info_log_file = "/nfs/obelix/raid2/msavasci/SLO-Power-Experiments/SLO-Power/Experiment-310/info_log.txt"

# This method returns [average response time, perct, #req/s, log_data, drop_rate, arrival_rate, service_rate] in this order
# def sample_log(log_file, percentile, sampling_time):
#     log_lines = []

#     # opening file using with so that file get closed after completing work 
#     with open(log_file) as f: 
#         # loop to read iterate log lines and store it in list
#         log_lines = f.readlines()

#     # TO DO: 16, 17 depend on date. For one digit days, 17. For two days numbers, 16. So, fix this issue.
#     # proc1 = subprocess.run(['cut', '-d', ' ', '-f', '16', log_file], stdout=subprocess.PIPE)
#     proc1 = subprocess.run(['cut', '-d', ' ', '-f', '17', log_file], stdout=subprocess.PIPE)
#     proc2 = subprocess.run(['cut', '-d', '/', '-f', '1'], input=proc1.stdout, stdout=subprocess.PIPE)
#     proc3 = subprocess.run(['sort', '-n'], input=proc2.stdout, stdout=subprocess.PIPE)
#     proc4 = subprocess.run(['uniq', '-c'], input=proc3.stdout, stdout=subprocess.PIPE)
#     proc5 = subprocess.run(['tail', '-n', '1'], input=proc4.stdout, stdout=subprocess.PIPE)
#     output = proc5.stdout.decode('utf-8').strip()

#     occurrence = int(output.split()[0])
#     max_arrival_rate = int(output.split()[1])

#     arrival_rate = max_arrival_rate
    
#     # req/s should be same with arrival rate.
#     request_per_second = arrival_rate
    
#     proc1 = subprocess.run(['cat', log_file], stdout=subprocess.PIPE)
#     proc2 = subprocess.run(['halog', '-srv', '-q'], input=proc1.stdout, stdout=subprocess.PIPE)
#     proc3 = subprocess.run(['tail', '-n', '1'], input=proc2.stdout, stdout=subprocess.PIPE)
#     output = proc3.stdout.decode('utf-8').strip()
    
#     # average_rt = float("{:.2f}".format(int(output.split()[11]))) # Return as millisecond
#     average_rt = int(output.split()[11]) # Return as millisecond
#     service_rate = math.ceil(int(output.split()[2]) / sampling_time)
#     # 5xx response codes / all response codes, so drop rate
#     drop_rate = round(int(output.split()[5]) / int(output.split()[7]), 2)

#     proc4 = subprocess.run(['halog', '-q', '-pct'], input=proc1.stdout, stdout=subprocess.PIPE)
#     proc5 = subprocess.run(['grep', percentile], input=proc4.stdout, stdout=subprocess.PIPE)
#     output = proc5.stdout.decode('utf-8').strip()

#     perct = int(float(output.split()[4]))
    
#     # Clean the log file.
#     subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)

#     return average_rt, perct, request_per_second, log_lines, drop_rate, arrival_rate, service_rate

def sample_log(log_file, percentile, sampling_time):
    log_lines, response_times = [], []
    count_all_response_codes, count_not_200_response_codes = 0, 0

    # opening file using with so that file get closed after completing work 
    with open(log_file) as f: 
        # read log lines and store it in list
        log_lines = f.readlines()

    # TO DO: 16, 17 depend on date. For one digit days, 17. For two days numbers, 16. So, fix this issue.
    proc1 = subprocess.run(['cut', '-d', ' ', '-f', '16', log_file], stdout=subprocess.PIPE)
    # proc1 = subprocess.run(['cut', '-d', ' ', '-f', '17', log_file], stdout=subprocess.PIPE)
    proc2 = subprocess.run(['cut', '-d', '/', '-f', '1'], input=proc1.stdout, stdout=subprocess.PIPE)
    proc3 = subprocess.run(['sort', '-n'], input=proc2.stdout, stdout=subprocess.PIPE)
    proc4 = subprocess.run(['uniq', '-c'], input=proc3.stdout, stdout=subprocess.PIPE)
    proc5 = subprocess.run(['tail', '-n', '1'], input=proc4.stdout, stdout=subprocess.PIPE)
    output = proc5.stdout.decode('utf-8').strip()

    occurrence = int(output.split()[0])
    max_arrival_rate = int(output.split()[1])

    arrival_rate = max_arrival_rate
    
    # req/s should be same with arrival rate.
    request_per_second = arrival_rate

    for incoming_requests in log_lines:
        splitted = str(incoming_requests).split()
        
        if len(splitted) < 21:
            continue
        
        response_code_info = splitted[10]
        page_info = splitted[18]
        response_time_info = int(splitted[20])

        if page_info.strip().startswith('/gw'):
            count_all_response_codes += 1

            if response_code_info.strip() == "200":  
                response_times.append(response_time_info)
            
            else:
                count_not_200_response_codes += 1
    
    drop_rate = count_not_200_response_codes / count_all_response_codes

    average_rt = stat.mean(response_times)

    perct = np.percentile(response_times, percentile)

    service_rate = int(count_all_response_codes / sampling_time)

    # proc1 = subprocess.run(['cat', log_file], stdout=subprocess.PIPE)
    # proc2 = subprocess.run(['halog', '-srv', '-q'], input=proc1.stdout, stdout=subprocess.PIPE)
    # proc3 = subprocess.run(['tail', '-n', '1'], input=proc2.stdout, stdout=subprocess.PIPE)
    # output = proc3.stdout.decode('utf-8').strip()
    
    # # average_rt = float("{:.2f}".format(int(output.split()[11]))) # Return as millisecond
    # average_rt = int(output.split()[11]) # Return as millisecond
    # service_rate = math.ceil(int(output.split()[2]) / sampling_time)
    # # 5xx response codes / all response codes, so drop rate
    # drop_rate = round(int(output.split()[5]) / int(output.split()[7]), 2)

    # proc4 = subprocess.run(['halog', '-q', '-pct'], input=proc1.stdout, stdout=subprocess.PIPE)
    # proc5 = subprocess.run(['grep', percentile], input=proc4.stdout, stdout=subprocess.PIPE)
    # output = proc5.stdout.decode('utf-8').strip()

    # perct = int(float(output.split()[4]))
    
    # Clean the log file.
    subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)
    
    return average_rt, perct, request_per_second, log_lines, drop_rate, arrival_rate, service_rate


def write_to_file( measured_response_time_data, tail_response_time_data, drop_percentage, estimated_number_of_request_data, measured_server_power_data, cpu_util_data, cpu_freq_data, allocated_cores, log_data):
    with open(f_measured_rt, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in measured_response_time_data))

    with open(f_tail_rt, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in tail_response_time_data))

    with open(f_drop_percent, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in drop_percentage))    

    with open(f_est_number_of_request, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in estimated_number_of_request_data))
    
    with open(f_measured_server_power, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]}),' for tup in measured_server_power_data))

    with open(f_cpu_util, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]},{tup[3]}),' for tup in cpu_util_data))

    with open(f_cpu_freq, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]}),' for tup in cpu_freq_data))

    with open(f_allocated_number_of_cores, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in allocated_cores))

    with open(f_log_data, 'wb') as filehandle:
        pickle.dump(log_data, filehandle)


# This method returns the hash of the last modification time of given file_name.
def hash_of_file(file_name):
    modify_time = os.path.getmtime(file_name)
    # print(modify_time)
    hashed_object = hash(modify_time)
    # print(hashed_object)
    # print()
    return hashed_object


def retrieve_cpu_freq_information(machine_ip, machine_port, container_name):
    with grpc.insecure_channel(f'{machine_ip}:{machine_port}') as channel:
        stub = pb2_container_service_grpc.ContainerServiceStub(channel)
        s = stub.retrieve_cpu_freq_information( pb2_container_service.Container_Service_Input(domain_name=container_name))
        return s.cpu_freq
    

def retrieve_container_core_information(machine_ip, machine_port, container_name):
    with grpc.insecure_channel(f'{machine_ip}:{machine_port}') as channel:
        stub = pb2_container_service_grpc.ContainerServiceStub(channel)
        response = stub.retrieve_container_core_information(pb2_container_service.Container_Service_Input(domain_name=container_name))
    
        return response.number_of_cores
    

def retrieve_container_cpu_usage_information(machine_ip, machine_port, container_name):
    cpu_usage = 0.99
    
    with grpc.insecure_channel(f'{machine_ip}:{machine_port}') as channel:
        stub = pb2_container_service_grpc.ContainerServiceStub(channel)
        s = stub.retrieve_container_cpu_usage_information( pb2_container_service.Container_Service_Input(domain_name=container_name))
        cpu_usage = min(cpu_usage, s.cpu_usage)

        return cpu_usage
            

def retrieve_cpu_power_consumption(machine_ip, machine_port):
    with grpc.insecure_channel(f'{machine_ip}:{machine_port}') as channel:
        stub = pb2_monitor_grpc.PowerMonitorStub(channel)
        avg_power = stub.average_power( pb2_monitor.No_Input() )
    
        return avg_power.power_value
    

def run_core_allocator(host, port, vm_name, number_of_cores):
    with grpc.insecure_channel(f'{host}:{port}') as channel:
        stub = pb2_core_allocator_grpc.DynamicCoreAllocatorStub(channel)
        response = stub.allocate_core( pb2_core_allocator.Core_Inputs(domain_name=vm_name, number_of_cores=number_of_cores))
        
        return response.status


def run_monitor(sampling_time, application_sub_path, log_file):
    ''' To keep configuration variables '''
    config_dict = {}

    with open(config_file, "r") as f:
        config_dict = json.load(f)

    recording_frequency = config_dict["system_configs"]["recording_frequency"]
    min_core = config_dict["system_configs"]['min_core']
    max_core = config_dict["system_configs"]['max_core']
    rt_percentile = config_dict["system_configs"]["rt_percentile"]
    cluster_size = config_dict["system_configs"]["cluster_size"]

    print(f"Min core: {min_core}, Max core: {max_core * cluster_size}")

    # Define lists holding measurements done during experiment
    real_response_time_data, tail_response_time, estimated_number_of_request_data, drop_percentage, measured_server_power, cpu_util, cpu_freq, allocated_cores =  [], [], [], [], [], [], [], []

    log_records = {}

    with open(machines_config_file) as f:
        machines = json.load(f)

    runtime_container_core_dist = {}

    for m1 in machines["machines"]["container_service"]:
        for m2 in m1["container_name"]:
            runtime_container_core_dist[(m1["ip"], m2)] = retrieve_container_core_information(m1["ip"], m1["port"], m2)

    print(f"Current core info of containers: {runtime_container_core_dist}")

    curr_core = sum(runtime_container_core_dist.values())

    print(f"Total core info: {curr_core}")

    iteration_counter = 0

    cpu_util_threshold = 0.8

    initial_wait_flag = True

    while True:
        prev_hash = hash_of_file(log_file)
        
        time.sleep(1)

        if prev_hash != hash_of_file(log_file):
            break

    time.sleep(10)

    recording_start_time = timeit.default_timer()

    subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)

    print("HAProxy log file is cleared for the initialization purpose.")

    while True:
        tm_cpu_list = []

        # if initial_wait_flag == True:
        #     # time.sleep(sampling_time * max(cpu_util_window_size, request_rate_window_size))
        #     time.sleep(sampling_time * 2)
        #     subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)
        #     initial_wait_flag = False

        runtime_container_cpu_util = {}

        if timeit.default_timer() - recording_start_time >= recording_frequency:
            print("Recording to log file...")

            write_to_file( real_response_time_data, tail_response_time, drop_percentage, estimated_number_of_request_data, measured_server_power, cpu_util, cpu_freq, allocated_cores, log_records)

            real_response_time_data, tail_response_time, estimated_number_of_request_data, drop_percentage, measured_server_power, cpu_util, cpu_freq, allocated_cores = [], [], [], [], [], [], [], []

            recording_start_time = timeit.default_timer()

        time.sleep(sampling_time)

        mean_response_time, percent_rt, estimated_number_of_request, log, drop, arrival_rate, service_rate = sample_log(log_file, rt_percentile, sampling_time)
        
        if mean_response_time <= 1:
            print(f"No (logical) response time has been read; therefore, wait for {sampling_time} seconds.")
            continue

        iteration_counter += 1

        print(f"Iteration: {iteration_counter}, Estimated number of request: {estimated_number_of_request}, Average response time: {mean_response_time}, {rt_percentile}th response time: {percent_rt}")
        # Adding average response time into the list
        real_response_time_data.append((iteration_counter, mean_response_time))
        # Adding estimated number of request value into the list
        estimated_number_of_request_data.append((iteration_counter, estimated_number_of_request))
        # Adding drop percentage into the list.
        drop_percentage.append((iteration_counter, drop))
        # Adding {rt_percentile}th response time info into the list.
        tail_response_time.append((iteration_counter, percent_rt))
        # Adding log records into the dictionary.
        log_records[iteration_counter] = log

        # Retrieve power consumption information of nodes.
        for mac in machines["machines"]["power_monitor"]:
            measured_server_power.append((iteration_counter, str(mac["ip"]), retrieve_cpu_power_consumption(mac["ip"], mac["port"])))

        # Retrieve cpu frequency information of nodes and cpu utilization information of containers.
        for mac in machines["machines"]["container_service"]:
            cpu_freq.append((iteration_counter, str(mac["ip"]), retrieve_cpu_freq_information(mac["ip"], mac["port"], "")))

            for c1 in mac["container_name"]:
                tmp_cpu_util = retrieve_container_cpu_usage_information(mac["ip"], mac["port"], c1)
                tm_cpu_list.append(tmp_cpu_util)
                cpu_util.append((iteration_counter, str(mac["ip"]), str(c1), tmp_cpu_util))
                runtime_container_cpu_util[(mac["ip"], c1)] = tmp_cpu_util

        for k1 in runtime_container_cpu_util:
            # if runtime_container_cpu_util[k1] > cpu_util_threshold:
            #     # curr_number_of_core = min( max( min_core,  math.ceil(curr_number_of_core * ( cpu_utilization / cpu_util_threshold )) ), max_core )
            #     runtime_container_core_dist[k1] = min( max( min_core,  math.ceil(runtime_container_core_dist[k1] * ( runtime_container_cpu_util[k1] / cpu_util_threshold )) ), max_core )
            runtime_container_core_dist[k1] = min( max( min_core,  math.ceil(runtime_container_core_dist[k1] * ( stat.mean(tm_cpu_list) / cpu_util_threshold )) ), max_core )

        curr_core = sum(runtime_container_core_dist.values())  

        # if cpu_utilization > cpu_util_threshold:
        #     curr_number_of_core = curr_number_of_core + 1

        # elif (cpu_utilization * curr_number_of_core / (curr_number_of_core - 1)) < cpu_util_threshold:
        #     curr_number_of_core = curr_number_of_core - 1

        # curr_number_of_core = min( max( min_core, math.ceil(estimated_number_of_request / service_rate_override) + int(max_core / 2) ), max_core )
        
        # print(runtime_container_core_dist)

        for m1 in machines["machines"]["core_allocator"]:
            for m2 in m1["container_name"]:
                step1_output = run_core_allocator(m1["ip"], m1["port"], m2, runtime_container_core_dist[(m1["ip"], m2)])
        
                if step1_output == True:
                    print(f"{runtime_container_core_dist[(m1['ip'], m2)]} core(s) has been allocated to {m2} hosted on {m1['ip']}.")
                    
                else:
                    with open(info_log_file, "a") as f:
                        f.write(f"Iteration: {iteration_counter} - core(s) could not been allocated for the container {m2} hosted on {m1['ip']}. So, the current number of core {runtime_container_core_dist[(m1['ip'], m2)]} remains in effect!\n")
            
        allocated_cores.append((iteration_counter, curr_core))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Application Monitoring Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-rt", "--measured-rt", default="./data/real-rt.txt", help="File to keep measured response time")
    
    parser.add_argument("-trt", "--measured-tail-rt", default="./data/tail-rt.txt", help="File to keep measured tail response times")
    
    parser.add_argument("-dp", "--drop-percent", default="./data/drop-percentage.txt", help="File to keep percentage of dropped requests")
    
    parser.add_argument("-er", "--est-number-of-request", default="./data/est-number-of-request.txt", help="File to keep estimated number of request")
    
    parser.add_argument("-sp", "--measured-server-power", default="./data/measured_server_power.txt", help="File to measured server power")

    parser.add_argument("-nc", "--number-of-cores", default="./data/number_of_cores.txt", help="File to keep allocated number of cores")
    
    parser.add_argument("-cu", "--cpu-utilization", default="./data/cpu_utilization.txt", help="File to keep cpu utilization")

    parser.add_argument("-cf", "--cpu-frequency", default="./data/cpu_frequency.txt", help="File to keep cpu frequency")

    parser.add_argument("-ld", "--log-data", default="./data/log_data.txt", help="File to keep log data")

    parser.add_argument("-l", "--log-file", default="./data/log-file.txt", help="HAProxy log file")

    parser.add_argument("-s", "--sampling-time", type=int, default="./data/sampling_time", help="sampling time")

    args = parser.parse_args()

    f_measured_rt = args.measured_rt                        # File for measured response time
    f_tail_rt = args.measured_tail_rt                       # File for tail response time
    f_drop_percent = args.drop_percent                      # File for keeping drop percentage
    f_est_number_of_request = args.est_number_of_request    # File for keeping estimating number of requests
    f_measured_server_power = args.measured_server_power    # File for keeping measured server power consumption
    f_allocated_number_of_cores = args.number_of_cores      # File for keeping allocated number of cores
    f_cpu_util = args.cpu_utilization                       # File for keeping cpu utilization
    f_cpu_freq = args.cpu_frequency                         # File for keeping cpu frequency
    f_log_data = args.log_data                              # File for keeping haproxy log data

    run_monitor(args.sampling_time, "/gw", args.log_file)
