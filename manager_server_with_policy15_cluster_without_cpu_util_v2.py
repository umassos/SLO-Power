import grpc
from concurrent import futures
from Utility import Utility
import manager_pb2 as pb2_mgr
import manager_pb2_grpc as pb2_mgr_grpc
import power_capper_pb2 as pb2_pwr
import power_capper_pb2_grpc as pb2_pwr_grpc
import dynamic_core_allocator_pb2 as pb2_core_allocator
import dynamic_core_allocator_pb2_grpc as pb2_core_allocator_grpc
import container_service_pb2 as pb2_container_service
import container_service_pb2_grpc as pb2_container_service_grpc
import rapl_power_monitor_pb2 as pb2_monitor
import rapl_power_monitor_pb2_grpc as pb2_monitor_grpc
import argparse
import pandas as pd
import numpy as np
import time
import timeit
import statistics as stat
import math
import subprocess
import pickle
import json
import os
from datetime import datetime

f_allocated_power_data, f_estimated_power_data, f_real_rt, f_tail_rt, f_filtered_rt, f_log_file, f_error_value, f_drop_percent, f_est_number_of_request, f_service_rate, f_p_terms, f_i_terms, f_operating_points, f_integrator, f_integral_switch_on_off, f_allocated_number_of_core_data, f_reactively_allocated_number_of_core_data, f_proactively_allocated_number_of_core_data, f_measured_server_power, f_cpu_util, f_cpu_freq, f_rate_best_fit, f_cpu_util_best_fit, f_to_be_increased_core_list, f_to_be_reduced_core_list = "", "", "", "", "", "", "", "", "", "", "",  "", "", "",  "", "", "", "", "", "", "", "", "", "", ""

# Instantiate Utility class to use utilities such as 'converting from second to millisecond', etc.
my_utility = Utility()

core_congestion_threshold = 8

# machines_config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/machines.csv"
# machines_config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/cluster_machines.json"
machines_config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/cluster_machines.json"
# config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/power_manager_config.csv"
config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/power_manager_config.json"
info_log_file = "/nfs/obelix/raid2/msavasci/SLO-Power-Experiments/SLO-Power/Experiment-423/info_log.txt"

# core_power_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/core_power_consumption.csv"

class ControlUnit:
    def __init__(self, up_threshold, down_threshold) -> None:
        self.counter_up = 0
        self.counter_down = 0
        self.up_threshold = up_threshold
        self.down_threshold = down_threshold

    def vertical_scaler(self, target_response_time, arrival_rate, service_rate):
        return min(max(self.min_core, self.core_estimator(target_response_time, arrival_rate, service_rate)), self.max_core)

    def core_estimator(self, target_response_time, arrival_rate, service_rate):
        # It is according to [Liang et al.(2022)]
        return math.ceil( (arrival_rate * target_response_time) / (service_rate * target_response_time - 1) )


class PIController():
    def __init__(self, min, max):
        self.kp = 0.0
        self.ki = 0.0
        self.operating_point_control_value = 0.0
        self.operating_point_output_value = 0.0
        self.min_limit = min
        self.max_limit = max

    def set_parameters(self, kp, ki, cv, ov):
        self.kp = kp
        self.ki = ki
        self.operating_point_control_value = cv
        self.operating_point_output_value = ov


class Machine():
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port


# A class for handling controller generator service
class PowerManager(pb2_mgr_grpc.PowerManagerServicer):
    # Implementation of interface method defined in proto file.
    def begin_power_manager(self, request, context):
        # reqs, kp, ki, pwr, rt, a, b = initialize_controller(request.controller_data_file)
        # control_unit_object = initialize_control_unit_object()
        control_unit_object = []
        print("Initializing the control unit object is done")
        run_manager(PIController(request.pi_min, request.pi_max), control_unit_object, request.number_of_lines_to_be_read, request.sampling_time, request.tune_percentage, request.application_sub_path, request.ref_input, request.log_file, request.retraining_threshold)


def core_power_limit(number_of_cores):
    # This equation derived from core_power experiment. intel pstate driver with powersave governor.
    # return math.ceil(2.81 * number_of_cores + 44.95)

    # This equation derived from core_power experiment. acpi_freq driver with performance governor.
    return math.floor(2.86 * number_of_cores + 46.52)


def initialize_control_unit_object():
    ''' Configuration variables '''
    config_dict = {}

    with open(config_file) as cf:
        for line in cf:
            splitted = line.split(',')
            config_dict[splitted[0].strip()] = int(splitted[1].strip())

    return ControlUnit(config_dict['up_threshold'], config_dict['down_threshold'])


# This method returns [average response time, perct, #req/s, log_data, drop_rate, arrival_rate, service_rate] in this order
def sample_log(log_file, percentile, sampling_time):
    print(f"sampling start: {datetime.now()}")
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
    
    print(f"sampling end: {datetime.now()}")
    return response_times, average_rt, perct, request_per_second, log_lines, drop_rate, arrival_rate, service_rate

def write_to_file( allocated_power_data, measured_response_time_data, tail_response_time_data, error_data, drop_percentage, estimated_number_of_request_data, log_data, allocated_number_of_core_data, reactively_allocated_number_of_core_data, proactively_allocated_number_of_core_data, measured_server_power_data, cpu_util_data, service_rate_data, cpu_freq_data ):
    with open(f_allocated_power_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in allocated_power_data))

    with open(f_measured_rt, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in measured_response_time_data))

    with open(f_tail_rt, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in tail_response_time_data))

    with open(f_error_value, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in error_data))        

    with open(f_drop_percent, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in drop_percentage))    

    with open(f_est_number_of_request, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in estimated_number_of_request_data))
    
    with open(f_allocated_number_of_core_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in allocated_number_of_core_data))

    with open(f_reactively_allocated_number_of_core_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in reactively_allocated_number_of_core_data))

    with open(f_proactively_allocated_number_of_core_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in proactively_allocated_number_of_core_data))

    with open(f_measured_server_power, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in measured_server_power_data))

    with open(f_cpu_util, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in cpu_util_data))

    with open(f_service_rate, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in service_rate_data))

    with open(f_cpu_freq, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in cpu_freq_data))

    with open(f_log_file, 'wb') as filehandle:
        pickle.dump(log_data, filehandle)


def write_to_file_upt( allocated_power_data, measured_response_time_data, tail_response_time_data, error_data, drop_percentage, estimated_number_of_request_data, log_data, allocated_number_of_core_data, reactively_allocated_number_of_core_data, proactively_allocated_number_of_core_data, measured_server_power_data, cpu_util_data, service_rate_data, cpu_freq_data, best_fit_req_rate, best_fit_cpu_util, to_be_increased_list, to_be_reduced_list ):
    with open(f_allocated_power_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in allocated_power_data))

    with open(f_measured_rt, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in measured_response_time_data))

    with open(f_tail_rt, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in tail_response_time_data))

    with open(f_error_value, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in error_data))        

    with open(f_drop_percent, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in drop_percentage))    

    with open(f_est_number_of_request, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in estimated_number_of_request_data))
    
    with open(f_allocated_number_of_core_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in allocated_number_of_core_data))

    with open(f_reactively_allocated_number_of_core_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in reactively_allocated_number_of_core_data))

    with open(f_proactively_allocated_number_of_core_data, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in proactively_allocated_number_of_core_data))

    with open(f_measured_server_power, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]}),' for tup in measured_server_power_data))

    with open(f_cpu_util, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]},{tup[3]}),' for tup in cpu_util_data))

    with open(f_cpu_freq, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]}),' for tup in cpu_freq_data))

    with open(f_service_rate, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in service_rate_data))

    with open(f_rate_best_fit, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in best_fit_req_rate))

    with open(f_cpu_util_best_fit, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in best_fit_cpu_util))

    with open(f_to_be_increased_core_list, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in to_be_increased_list))

    with open(f_to_be_reduced_core_list, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]}),' for tup in to_be_reduced_list))

    with open(f_log_file, 'wb') as filehandle:
        pickle.dump(log_data, filehandle)


def run_core_allocator(host, port, vm_name, number_of_cores):
    with grpc.insecure_channel(f'{host}:{port}') as channel:
        stub = pb2_core_allocator_grpc.DynamicCoreAllocatorStub(channel)
        response = stub.allocate_core( pb2_core_allocator.Core_Inputs(domain_name=vm_name, number_of_cores=number_of_cores))
        
        return response.status
    

def run_power_allocator(host, port, allocated_power, cpu_package_count):
    with grpc.insecure_channel(f'{host}:{port}') as channel:
        stub = pb2_pwr_grpc.PowerCapperStub(channel)
        response = stub.cap_power( pb2_pwr.Cap_Input( power_cap=int(my_utility.convert_from_watt_to_microwatt(allocated_power/cpu_package_count)) ) )

        return response.status


def proactive_core_estimator(response_time_window, arrival_rate_window, service_rate_window, target_rt, arrival_rate_window_size):
    # arrival_rate = max(arrival_rate_window)
    if len(arrival_rate_window) == 1:
        arrival_rate = max(arrival_rate_window)

    else:
        arrival_rate = return_best_fit_point(arrival_rate_window, arrival_rate_window_size)
    
    # service_rate = min(service_rate_window)
    # service_rate = stat.mean(service_rate_window)
    service_rate = 24
    # prct = np.percentile(response_time_window, percentile)
    # response_time = my_utility.convert_from_millisecond_to_second(prct)
    expected_response_time = my_utility.convert_from_millisecond_to_second(target_rt)

    print(f"Arrival rate: {arrival_rate}, service rate: {service_rate}, expected response time: {expected_response_time} s")
    
    try:
        # It is according to [Liang et al.(2022)]
        return math.ceil( (arrival_rate * expected_response_time) / (service_rate * expected_response_time - 1) )
    except ZeroDivisionError as e:
        return -1


def reactive_step_slow(scaling_flag, curr_number_of_core, step_limit):
    if scaling_flag == "up":
        return curr_number_of_core + step_limit
    
    if scaling_flag == "down":
        return curr_number_of_core - step_limit
    

def reactive_step_adaptive(scaling_flag, curr_number_of_core, target_rt, curr_rt, step_limit, ratio):
    sigma = target_rt * ratio

    step_control = (target_rt - curr_rt) / sigma

    if scaling_flag == "up":
        return curr_number_of_core - (step_control * step_limit)

    if scaling_flag == "down":
        return curr_number_of_core - (step_control * step_limit)


def reactive_step_ratio(scaling_flag, curr_number_of_core, target_rt, curr_rt, step_limit):
    return math.ceil(target_rt * curr_number_of_core / curr_rt)


def reactive_core_estimator2(scaling_flag, curr_number_of_core):
    if scaling_flag == "up":
        if curr_number_of_core < core_congestion_threshold:
            return pow(2, curr_number_of_core)
        
        else:
            return curr_number_of_core + 1
        
    if scaling_flag == "down":
        return int(curr_number_of_core / 2)
    

def reactive_core_estimator3(scaling_flag, curr_number_of_core):
    if scaling_flag == "up":
        if curr_number_of_core < core_congestion_threshold:
            return pow(2, curr_number_of_core)
        
        else:
            return curr_number_of_core + 1
        
    if scaling_flag == "down":
        return curr_number_of_core - 1
    

def reactive_core_estimator4(scaling_flag, curr_number_of_core):
    if scaling_flag == "up":
        if curr_number_of_core < core_congestion_threshold:
            return 2 * curr_number_of_core
        
        else:
            return curr_number_of_core + 1
        
    if scaling_flag == "down":
        return curr_number_of_core - 1


def reactive_core_estimator5(scaling_flag, estimated_number_of_request, service_rate, curr_number_of_core):
    required_number_of_core = math.ceil( (estimated_number_of_request - service_rate) / service_rate )
    
    if scaling_flag == "up":
        return curr_number_of_core + required_number_of_core
        
    if scaling_flag == "down":
        return curr_number_of_core - required_number_of_core


def reactive_vertical_scaler(min_core, max_core, curr_number_of_core, scaling_flag, step_size):
    return min(max(min_core, reactive_step_slow(scaling_flag, curr_number_of_core, step_size)), max_core)


def proactive_vertical_scaler(min_core, max_core, response_time_window, arrival_rate_window, service_rate_window, target_rt, scaling_confidence_value, arrival_rate_window_size):
    output = proactive_core_estimator(response_time_window, arrival_rate_window, service_rate_window, target_rt, arrival_rate_window_size)

    if output == -1:
        return -1

    return min(max(min_core, output), max_core)


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
    

# This method returns the hash of the last modification time of given file_name.
def hash_of_file(file_name):
    modify_time = os.path.getmtime(file_name)
    # print(modify_time)
    hashed_object = hash(modify_time)
    # print(hashed_object)
    # print()
    return hashed_object


def invoke_reactive_vertical_scaler(error, power_cap, min_power, max_power, min_core, max_core, curr_number_of_core):
    if error < 0 and power_cap == max_power:
        reactive_number_of_core = reactive_vertical_scaler(min_core, max_core, curr_number_of_core, "up")
                
    if error > 0 and power_cap == min_power:
        reactive_number_of_core = reactive_vertical_scaler(min_core, max_core, curr_number_of_core, "down")

    return reactive_number_of_core


def error_to_power(error_value):
    abs_error = abs(error_value)

    if abs_error <= 0.25:
        return 2
    
    if abs_error > 0.25 and abs_error <= 0.5:
        return 4
    
    if abs_error > 0.5:
        return 8    
    

def required_number_of_core(arrival_rate, service_rate, target_rt):
    expected_response_time = my_utility.convert_from_millisecond_to_second(target_rt)

    return math.ceil( (arrival_rate * expected_response_time) / (service_rate * expected_response_time - 1) )


def return_best_fit_point(point_window, window_size):
    if len(point_window) < window_size:
        return max(point_window)
    
    x = np.arange(window_size)
    y = np.array(point_window[-window_size:])

    coeff = np.polyfit(x, y, 1)

    yn = np.poly1d(coeff)

    return yn(window_size)


def run_manager(pi_controller, control_unit, number_of_lines_to_be_read, sampling_time, tune_percentage, application_sub_path, ref_input, log_file, retraining_threshold):
    ''' To keep configuration variables '''
    config_dict = {}

    with open(config_file, "r") as f:
        config_dict = json.load(f)

    recording_frequency = config_dict["system_configs"]["recording_frequency"]
    min_core = config_dict["system_configs"]['min_core']
    max_core = config_dict["system_configs"]['max_core']
    proactive_scaling_timeout = config_dict["system_configs"]['proactive_scaling_timeout']
    power_scaling_confidence_value = config_dict["system_configs"]['power_confidence']
    number_of_cpu_sockets = config_dict["system_configs"]["number_of_cpu_sockets"]
    rt_percentile = config_dict["system_configs"]["rt_percentile"]
    vertical_scaler_confidence = config_dict["system_configs"]["vertical_scaler_confidence"]
    power_decrement_coefficient = config_dict["system_configs"]["power_decrement_coefficient"]
    reactive_scale_up_threshold = config_dict["system_configs"]["up_threshold"]
    reactive_scale_down_threshold = config_dict["system_configs"]["down_threshold"]
    cluster_size = config_dict["system_configs"]["cluster_size"]
    reactive_scaling_down_min_step_size = config_dict["system_configs"]["reactive_scaling_down_min_step_size"]
    reactive_scaling_up_min_step_size = config_dict["system_configs"]["reactive_scaling_up_min_step_size"]
    slo_guard = config_dict["system_configs"]["slo_guard"]
    request_rate_window_size = config_dict["system_configs"]["request_rate_window_size"]
    cpu_util_window_size = config_dict["system_configs"]["cpu_util_window_size"]
    # power_reduction_rate = config_dict["system_configs"]["power_reduction_rate"] # This value is based on increment power values in watts in RAPL.
    power_step = config_dict["system_configs"]['power_step']
    power_scale_down_cpu_util_threshold = config_dict["system_configs"]["power_scale_down_cpu_util_threshold"] 
    
    print(f"Min core: {min_core}, Max core: {max_core * cluster_size}")

    # power_capper_machines = []

    # df_machines = pd.read_csv(machines_config_file)

    # df_machines_filtered = df_machines[df_machines['description'] == 'power_allocator']

    # for _, model_line in df_machines_filtered.iterrows():
    #     power_capper_machines.append(Machine(str(model_line['machine_ip']), int(model_line['port'])))

    # core_allocator_machines = []

    # df_machines_filtered = df_machines[df_machines['description'] == 'core_allocator']

    # for _, model_line in df_machines_filtered.iterrows():
    #     core_allocator_machines.append(Machine(str(model_line['machine_ip']), int(model_line['port'])))

    # container_servicer_machines = []

    # df_machines_filtered = df_machines[df_machines['description'] == 'container_service']

    # for _, model_line in df_machines_filtered.iterrows():
    #     container_servicer_machines.append(Machine(str(model_line['machine_ip']), int(model_line['port'])))

    # allocated_power_data, real_response_time_data, tail_response_time, error_data, estimated_number_of_request_data, drop_percentage, allocated_number_of_core, reactively_allocated_number_of_core, proactively_allocated_number_of_core, measured_server_power, cpu_util, service_rate_data, cpu_freq = [], [], [], [], [], [], [], [], [], [], [], [], []

    # Define list holding measurements/variables during experiment
    real_response_time_data, tail_response_time, error_data, estimated_number_of_request_data, drop_percentage, service_rate_data, allocated_power_data, allocated_number_of_core, reactively_allocated_number_of_core, proactively_allocated_number_of_core, best_fit_req_rate, best_fit_cpu_util, to_be_increased_list, to_be_decreased_list = [], [], [], [], [], [], [], [], [], [], [], [], [], []
    
    measured_server_power, cpu_util, cpu_freq = [], [], []

    log_records = {}

    # power_scaler_confidence_coefficient = 0.1

    # error_threshold = 0.1
    # rt_percentile = "95.0"

    with open(machines_config_file) as f:
        machines = json.load(f)

    machine_curr_number_of_cores = {}

    for m1 in machines["machines"]["container_service"]:
        for m2 in m1["container_name"]:
            machine_curr_number_of_cores[(m1["ip"], m2)] = retrieve_container_core_information(m1["ip"], m1["port"], m2)

    # curr_number_of_core = retrieve_container_core_information(container_servicer_machines, "mediawiki-54-1")

    machine_power_limits = {}

    for k1 in machine_curr_number_of_cores:
        machine_power_limits[k1] = core_power_limit(machine_curr_number_of_cores[k1])

    print(f"Current core info of containers: {machine_curr_number_of_cores}")
    print(f"Controller min power limit for node: {pi_controller.min_limit}")
    print(f"Controller max power limit for node: {machine_power_limits}")
    print(f"Target response time of the application: {ref_input} ms")

    initial_proactive_scaling_flag = True

    response_times_window, arrival_rates_window, service_rates_window, = [], [], []

    iteration_counter = 0

    curr_power, curr_number_of_core = 0, 0

    counter_down = 0

    previous_number_of_request, estimated_number_of_request = 0, 0

    runtime_container_core_dist, container_core_reduction_state = {}, {}

    request_rate_window, cpu_util_window = [], []

    index_selected_container_for_core_reduction, to_be_reduced_number_of_core, track_to_be_reduced_number_of_core = 0, 0, 0

    initial_wait_flag = True

    print(f"Ref_input: {ref_input}")
    print(f"slo_guard: {slo_guard}")

    guarded_slo_target = ref_input * slo_guard

    print(f"Guarded SLO target: {guarded_slo_target}")

    while True:
        prev_hash = hash_of_file(log_file)
        
        time.sleep(1)

        if prev_hash != hash_of_file(log_file):
            break

    # time.sleep(5)
    time.sleep(10)

    proactive_scaler_start_time = timeit.default_timer()
    recording_start_time = timeit.default_timer()

    subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)

    print("HAProxy log file is cleared for the initialization purpose.")

    while True:
        # if initial_wait_flag == True:
        #     # time.sleep(sampling_time * max(cpu_util_window_size, request_rate_window_size))
        #     time.sleep(sampling_time * 2)
        #     subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)
        #     initial_wait_flag = False

        runtime_container_cpu_util, runtime_host_power_dist = {}, {}
        total_cpu_util, core_per_part, reactive_core = 0, 0, 0
        curr_cpu_util = 0
        tmp_power_measurements = []

        previous_number_of_request = estimated_number_of_request 

        if timeit.default_timer() - recording_start_time >= recording_frequency:
            print("Recording to log file...")
            write_to_file_upt(allocated_power_data, real_response_time_data, tail_response_time, error_data, drop_percentage, estimated_number_of_request_data, log_records, allocated_number_of_core, reactively_allocated_number_of_core, proactively_allocated_number_of_core, measured_server_power, cpu_util, service_rate_data, cpu_freq, best_fit_req_rate, best_fit_cpu_util, to_be_increased_list, to_be_decreased_list)

            real_response_time_data, tail_response_time, error_data, estimated_number_of_request_data, drop_percentage, service_rate_data, allocated_power_data, allocated_number_of_core, reactively_allocated_number_of_core, proactively_allocated_number_of_core, best_fit_req_rate, best_fit_cpu_util, to_be_increased_list, to_be_decreased_list = [], [], [], [], [], [], [], [], [], [], [], [], [], []
    
            measured_server_power, cpu_util, cpu_freq = [], [], []

            log_records = {}

            recording_start_time = timeit.default_timer()

        time.sleep(sampling_time)

        full_response_times, mean_response_time, percent_rt, estimated_number_of_request, log, drop, arrival_rate, service_rate = sample_log(log_file, rt_percentile, sampling_time)

        if mean_response_time <= 1:
            print(f"No (logical) response time has been read; therefore, wait for {sampling_time} seconds.")
            continue

        # service_rate = 3 # This is based on the measurement of Mediawiki application. Setup: intel_pstate driver with powersave governor.
        # service_rate = 9 # This is based on the measurement of Mediawiki application for a single server. Setup: acpi_cpufreq driver with performance governor.
        service_rate = 24 # This is based on the measurement of Mediawiki application for 3-machines setup. Setup: acpi_cpufreq driver with userpspace governor (2.1 GHz).

        response_times_window.append(percent_rt)
        arrival_rates_window.append(arrival_rate)
        service_rates_window.append(service_rate)

        # This part does initial configuration of the cluster when it first started.
        if initial_proactive_scaling_flag:
            print("Initial resource calibration is in progress...")
            proactive_number_of_core = proactive_vertical_scaler(min_core, max_core, response_times_window, arrival_rates_window, service_rates_window, guarded_slo_target, vertical_scaler_confidence, request_rate_window_size)

            cluster_proactive_number_of_core = proactive_number_of_core * cluster_size

            if proactive_number_of_core != -1:
                print(f"Proactive estimated number of core is {cluster_proactive_number_of_core}.")
                proactively_allocated_number_of_core.append((iteration_counter, cluster_proactive_number_of_core))

                # Retrieve cpu frequency information of nodes and cpu utilization information of containers.
                for mac in machines["machines"]["container_service"]:
                    for c1 in mac["container_name"]:
                        tmp_cpu_util = retrieve_container_cpu_usage_information(mac["ip"], mac["port"], c1)

                        if tmp_cpu_util > curr_cpu_util:
                            curr_cpu_util = tmp_cpu_util
                    
                        runtime_container_cpu_util[(mac["ip"], c1)] = tmp_cpu_util  

                # We have a $(cluster_size)-host cluster.
                # curr_number_of_core = min(cluster_size * max_core, proactive_number_of_core)
                # curr_number_of_core = proactive_number_of_core
                print(f"Proactively estimated number of core for cluster: {cluster_proactive_number_of_core}")

                print(runtime_container_cpu_util)

                for k1 in runtime_container_cpu_util:
                    runtime_container_core_dist[k1] = math.floor(cluster_proactive_number_of_core / cluster_size)

                curr_power = 0

                curr_number_of_core = sum(runtime_container_core_dist.values())

                print(runtime_container_core_dist)

                for m1 in machines["machines"]["core_allocator"]:
                    for m2 in m1["container_name"]:
                        step1_output = run_core_allocator(m1["ip"], m1["port"], m2, runtime_container_core_dist[(m1["ip"], m2)])
        
                        if step1_output == True:
                            # curr_number_of_core += runtime_container_core_dist[(m1["ip"], m2)]
                            # curr_number_of_core = max(curr_number_of_core, proactive_number_of_core)
                            print(f"{runtime_container_core_dist[(m1['ip'], m2)]} core(s) has been allocated to {m2} hosted on {m1['ip']}.")
                            
                            if core_power_limit(runtime_container_core_dist[(m1["ip"], m2)]) > curr_power:
                                curr_power = core_power_limit(runtime_container_core_dist[(m1["ip"], m2)])
                    
                        else:
                            with open(info_log_file, "a") as f:
                                f.write(f"Iteration: {iteration_counter} - {runtime_container_core_dist[(m1['ip'], m2)]} core(s) could not been allocated for the container {m2} hosted on {m1['ip']}. So, the current number of core {curr_number_of_core} remains in effect!\n")

                for m1 in machines["machines"]["power_allocator"]:
                    step2_output = run_power_allocator(m1["ip"], m1["port"], curr_power, number_of_cpu_sockets)    

                    if step2_output == True:
                        print(f"Power has been set to {curr_power} Watts on {m1['ip']} due to change in number of core by the proactive scaler.")

                    else:
                        with open(info_log_file, "a") as f:
                            f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_power} Watts (initialization phase) on {m1['ip']}. Thus, old power value stays in effect!\n")

                initial_proactive_scaling_flag = False
                
            else:
                with open(info_log_file, "a") as f:
                    f.write(f"Iteration: {iteration_counter} - # cores by proactive scaler in scaling up mode model is not changed because of the model error. Thus, the current number of core stays in effect!\n")

            response_times_window, arrival_rates_window, service_rates_window = [],[],[]
            proactive_scaler_start_time = timeit.default_timer()
            recording_start_time = timeit.default_timer()
            print("Initial resource calibration is done :)")
            continue

        iteration_counter += 1

        print(f"Iteration: {iteration_counter}, Estimated number of request: {estimated_number_of_request}, Average response time: {mean_response_time}, Tail response time: {percent_rt}")
        # Adding average response time into the list
        real_response_time_data.append((iteration_counter, mean_response_time))
        # Adding tail response time into the list
        tail_response_time.append((iteration_counter, percent_rt))
        # Adding estimated number of request value into the list
        estimated_number_of_request_data.append((iteration_counter, estimated_number_of_request))
        # Adding service rate value into the list
        service_rate_data.append((iteration_counter, service_rate))
        # Adding drop percentage into the list.
        drop_percentage.append((iteration_counter, drop))
        # Adding log data info into the list.
        log_records[iteration_counter] = log

        # curr_error = float("{:.2f}".format(my_utility.convert_from_millisecond_to_second(ref_input - mean_response_time)))
        # curr_error = ref_input - percent_rt - slo_guard
        curr_error = guarded_slo_target - percent_rt
        # Add error value into list.
        error_data.append((iteration_counter, curr_error))

        request_rate_window.append(arrival_rate)
        best_fit_req_rate.append((iteration_counter, return_best_fit_point(request_rate_window, request_rate_window_size)))

         # Retrieve power consumption information of nodes.
        for mac in machines["machines"]["power_monitor"]:
            tmp_pow = retrieve_cpu_power_consumption(mac["ip"], mac["port"])
            measured_server_power.append((iteration_counter, str(mac["ip"]), tmp_pow))
            tmp_power_measurements.append(tmp_pow)

        # Retrieve cpu frequency information of nodes and cpu utilization information of containers.
        for mac in machines["machines"]["container_service"]:
            cpu_freq.append((iteration_counter, str(mac["ip"]), retrieve_cpu_freq_information(mac["ip"], mac["port"], "")))

            for c1 in mac["container_name"]:
                tmp_cpu_util = retrieve_container_cpu_usage_information(mac["ip"], mac["port"], c1)
                cpu_util.append((iteration_counter, str(mac["ip"]), str(c1), tmp_cpu_util))
                runtime_container_cpu_util[(mac["ip"], c1)] = tmp_cpu_util

                if tmp_cpu_util > curr_cpu_util:
                    curr_cpu_util = tmp_cpu_util

        cpu_util_window.append(curr_cpu_util)
        best_fit_cpu_util.append((iteration_counter, return_best_fit_point(cpu_util_window, cpu_util_window_size)))

        if curr_error < 0:
            if curr_power >= math.floor(core_power_limit(curr_number_of_core / cluster_size)) - power_scaling_confidence_value:
                print("Reactive scaling up decision is gonna be taken...")
            
                # to_be_increased_number_of_core = min(max_core * cluster_size - curr_number_of_core, abs(required_number_of_core(estimated_number_of_request, service_rate, guarded_slo_target) - required_number_of_core(previous_number_of_request, service_rate, guarded_slo_target)) * cluster_size)

                # to_be_increased_number_of_core = min(max_core * cluster_size - curr_number_of_core, required_number_of_core(return_best_fit_point(request_rate_window, request_rate_window_size), service_rate, guarded_slo_target) * cluster_size)

                to_be_increased_number_of_core = min(max_core * cluster_size - curr_number_of_core, required_number_of_core(return_best_fit_point(request_rate_window, request_rate_window_size), service_rate, guarded_slo_target) * cluster_size - curr_number_of_core)

                print(f"To be increased # cores: {to_be_increased_number_of_core}")

                to_be_increased_list.append((iteration_counter, to_be_increased_number_of_core))

                if to_be_increased_number_of_core < 0:
                    # # Add allocated number of core into the list
                    # allocated_number_of_core.append((iteration_counter, curr_number_of_core))
                    # # Add allocated power into the list
                    # allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets))))
                    # continue
                    to_be_increased_number_of_core = reactive_scaling_up_min_step_size

                to_be_increased_list.append((iteration_counter, to_be_increased_number_of_core))

                core_increase = 0

                for k1 in runtime_container_cpu_util: 
                    core_increase = max(reactive_scaling_up_min_step_size, math.floor(to_be_increased_number_of_core))
                    
                    tmp_reactive_core = reactive_vertical_scaler(min_core, max_core, runtime_container_core_dist[k1], "up", core_increase)
                    reactive_core += tmp_reactive_core
                    runtime_container_core_dist[k1] = tmp_reactive_core  
                
                curr_number_of_core = sum(runtime_container_core_dist.values())
                reactively_allocated_number_of_core.append((iteration_counter, reactive_core))

                for m1 in machines["machines"]["core_allocator"]:
                    for m2 in m1["container_name"]:
                        step1_output = run_core_allocator(m1["ip"], m1["port"], m2, runtime_container_core_dist[(m1["ip"], m2)])
        
                        if step1_output == True:
                            # curr_number_of_core = reactive_core
                            # curr_number_of_core = max(curr_number_of_core, proactive_number_of_core)
                            print(f"{runtime_container_core_dist[(m1['ip'], m2)]} core(s) has been allocated to {m2} hosted on {m1['ip']}.")
                    
                        else:
                            with open(info_log_file, "a") as f:
                                f.write(f"Iteration: {iteration_counter} - {reactive_core} core(s) could not been allocated for the container {m2} hosted on {m1['ip']}. So, the current number of core {curr_number_of_core} remains in effect!\n")

                curr_power = min(core_power_limit(curr_number_of_core / cluster_size), (curr_power + power_step * core_increase))

                print(f"Power is being set to {curr_power} Watts (increase)")

                for m1 in machines["machines"]["power_allocator"]:
                    step1_output = run_power_allocator(m1["ip"], m1["port"], curr_power, number_of_cpu_sockets)    

                    if step1_output == True:
                        print(f"Power has been set to {curr_power} Watts on {m1['ip']} (Due to inner power scaler loop).")

                    else:
                        with open(info_log_file, "a") as f:
                            f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_power} Watts (Power increment case) on {m1['ip']}. Thus, old power value stays in effect!\n")
            
            else:
                power_increment_ratio = abs(curr_error / percent_rt)
                curr_power = min(core_power_limit(curr_number_of_core / cluster_size), math.ceil(curr_power + curr_power * power_increment_ratio))

                print(f"Power is being set to {curr_power} Watts (increase)")

                for m1 in machines["machines"]["power_allocator"]:
                    step1_output = run_power_allocator(m1["ip"], m1["port"], curr_power, number_of_cpu_sockets)    

                    if step1_output == True:
                        print(f"Power has been set to {curr_power} Watts on {m1['ip']} (Due to inner power scaler loop).")

                    else:
                        with open(info_log_file, "a") as f:
                            f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_power} Watts (Power increment case) on {m1['ip']}. Thus, old power value stays in effect!\n")

            counter_down = 0

            # Add allocated number of core into the list
            allocated_number_of_core.append((iteration_counter, curr_number_of_core))
            # Add allocated power into the list
            allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets)) ))
            continue
                
        elif curr_error > 0:
            if return_best_fit_point(cpu_util_window, cpu_util_window_size) > power_scale_down_cpu_util_threshold:
                print("Proactively scaling up decision is gonna be taken...")
            
                # to_be_increased_number_of_core = min(max_core * cluster_size - curr_number_of_core, abs(required_number_of_core(estimated_number_of_request, service_rate, guarded_slo_target) - required_number_of_core(previous_number_of_request, service_rate, guarded_slo_target)) * cluster_size) 

                to_be_increased_number_of_core = min(max_core * cluster_size - curr_number_of_core, required_number_of_core(return_best_fit_point(request_rate_window, request_rate_window_size), service_rate, guarded_slo_target) * cluster_size - curr_number_of_core)

                print(f"To be increased # cores: {to_be_increased_number_of_core}")

                to_be_increased_list.append((iteration_counter, to_be_increased_number_of_core))

                if to_be_increased_number_of_core < 0:
                    # # Add allocated number of core into the list
                    # allocated_number_of_core.append((iteration_counter, curr_number_of_core))
                    # # Add allocated power into the list
                    # allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets))))
                    # continue
                    to_be_increased_number_of_core = reactive_scaling_up_min_step_size

                to_be_increased_list.append((iteration_counter, to_be_increased_number_of_core))

                core_increase = 0

                for k1 in runtime_container_cpu_util: 
                    core_increase = max(reactive_scaling_up_min_step_size, math.floor(to_be_increased_number_of_core))
                    
                    tmp_reactive_core = reactive_vertical_scaler(min_core, max_core, runtime_container_core_dist[k1], "up", core_increase)
                    reactive_core += tmp_reactive_core
                    runtime_container_core_dist[k1] = tmp_reactive_core 
                
                curr_number_of_core = sum(runtime_container_core_dist.values())
                reactively_allocated_number_of_core.append((iteration_counter, reactive_core))

                # else:
                #     reactively_allocated_number_of_core.append((iteration_counter, curr_number_of_core))

                for m1 in machines["machines"]["core_allocator"]:
                    for m2 in m1["container_name"]:
                        step1_output = run_core_allocator(m1["ip"], m1["port"], m2, runtime_container_core_dist[(m1["ip"], m2)])
        
                        if step1_output == True:
                            # curr_number_of_core = reactive_core
                            # curr_number_of_core = max(curr_number_of_core, proactive_number_of_core)
                            print(f"{runtime_container_core_dist[(m1['ip'], m2)]} core(s) has been allocated to {m2} hosted on {m1['ip']}.")
                    
                        else:
                            with open(info_log_file, "a") as f:
                                f.write(f"Iteration: {iteration_counter} - {reactive_core} core(s) could not been allocated for the container {m2} hosted on {m1['ip']}. So, the current number of core {curr_number_of_core} remains in effect!\n")


                curr_power = min(core_power_limit(curr_number_of_core / cluster_size), (curr_power + power_step * core_increase))

                print(f"Power is being set to {curr_power} Watts (increase)")

                for m1 in machines["machines"]["power_allocator"]:
                    step1_output = run_power_allocator(m1["ip"], m1["port"], curr_power, number_of_cpu_sockets)    

                    if step1_output == True:
                        print(f"Power has been set to {curr_power} Watts on {m1['ip']} (Due to inner power scaler loop).")

                    else:
                        with open(info_log_file, "a") as f:
                            f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_power} Watts (Power increment case) on {m1['ip']}. Thus, old power value stays in effect!\n")

                # Add allocated number of core into the list
                allocated_number_of_core.append((iteration_counter, curr_number_of_core))
                # Add allocated power into the list
                allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets))))

                continue

            if curr_error <= 100:
                # Add allocated number of core into the list
                allocated_number_of_core.append((iteration_counter, curr_number_of_core))
                # Add power value into the list
                allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets))))

                continue

            counter_down += 1

            if counter_down >= reactive_scale_down_threshold:
                print("Reactive scaling down decision is gonna be taken...")

                # to_be_Reduced_number_of_core > cluster size??
                to_be_reduced_number_of_core = curr_number_of_core - required_number_of_core(return_best_fit_point(request_rate_window, request_rate_window_size), service_rate, guarded_slo_target) * cluster_size

                print(f"To be decreased # cores up to : {to_be_reduced_number_of_core}")

                to_be_decreased_list.append((iteration_counter, to_be_reduced_number_of_core))

                if to_be_reduced_number_of_core < cluster_size:
                    # Add allocated number of core into the list
                    allocated_number_of_core.append((iteration_counter, curr_number_of_core))
                    # Add allocated power into the list
                    allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets))))
                    continue

                for k1 in runtime_container_cpu_util:
                    tmp_reactive_core = reactive_vertical_scaler(min_core, max_core, runtime_container_core_dist[k1], "down", reactive_scaling_down_min_step_size)
                    runtime_container_core_dist[k1] = tmp_reactive_core

                curr_number_of_core = sum(runtime_container_core_dist.values())
                            
                for m1 in machines["machines"]["core_allocator"]:
                    for m2 in m1["container_name"]:
                        step1_output = run_core_allocator(m1["ip"], m1["port"], m2, runtime_container_core_dist[(m1["ip"], m2)])
        
                        if step1_output == True:
                            # curr_number_of_core = reactive_core
                            # curr_number_of_core = max(curr_number_of_core, proactive_number_of_core)
                            print(f"{runtime_container_core_dist[(m1['ip'], m2)]} core(s) has been allocated to {m2} hosted on {m1['ip']}.")
                    
                        else:
                            with open(info_log_file, "a") as f:
                                f.write(f"Iteration: {iteration_counter} - {reactive_core} core(s) could not been allocated for the container {m2} hosted on {m1['ip']}. So, the current number of core {curr_number_of_core} remains in effect!\n")
        
                counter_down = 0

                # Add allocated number of core into the list
                allocated_number_of_core.append((iteration_counter, curr_number_of_core))
                # Add allocated power into the list
                allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets))))
                continue

            else:
                with open(info_log_file, "a") as f:
                    f.write(f"Iteration: {iteration_counter} - scaling down value ({counter_down}) is less than {reactive_scale_down_threshold}. Current settings will be kept and we will see that if scale down decision is gonna be given in the next iteration!\n")
                
        if curr_power < (max(tmp_power_measurements) + max(tmp_power_measurements) * 0.1):
            # Add allocated number of core into the list
            allocated_number_of_core.append((iteration_counter, curr_number_of_core))
            allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets)) ))
            continue

        # if return_best_fit_point(cpu_util_window, cpu_util_window_size) > power_scale_down_cpu_util_threshold:
        #     # Add allocated number of core into the list
        #     allocated_number_of_core.append((iteration_counter, curr_number_of_core))
        #     allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets)) ))
        #     continue
        
        power_decrement_ratio = power_step / reactive_scale_down_threshold
        curr_power = math.floor(curr_power - power_decrement_ratio)

        print(f"Power is being set to {curr_power} Watts (decrease)")

        # Connect to local power agents and tell them to allocate 'curr_power' per CPU package.
        for m1 in machines["machines"]["power_allocator"]:
            step1_output = run_power_allocator(m1["ip"], m1["port"], curr_power, number_of_cpu_sockets)    

            if step1_output == True:
                print(f"Power has been set to {curr_power} Watts on {m1['ip']} (Due to inner power scaler loop).")

            else:
                with open(info_log_file, "a") as f:
                    f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_power} Watts (Power decrement case) on {m1['ip']}. Thus, old power value stays in effect!\n")

        # Add allocated number of core into the list
        allocated_number_of_core.append((iteration_counter, curr_number_of_core))
        allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_power/number_of_cpu_sockets)) ))


def serve(host, port, max_workers):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    pb2_mgr_grpc.add_PowerManagerServicer_to_server(PowerManager(), server)
    ''' 
    For using the insecure port
    '''
    # server.add_insecure_port(f"{host}:{port}")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Power Manager started on port {port} with {max_workers} workers.")
    server.wait_for_termination()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Power Manager Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-H", "--host", default="localhost",
                        help="Network host")
    parser.add_argument("-p", "--port", type=int, default=8090,
                        help="Network port")
    parser.add_argument("-w", "--workers", default=10,
                        type=int, help="Max Number of workers")
    
    # parser.add_argument("-th", "--threshold", type=int, required=True, help="Retraining threshold")
    parser.add_argument("-ap", "--allocated-power", default="./data/allocated-power.txt", help="File to keep allocated power")
    parser.add_argument("-ep", "--estimated-power", default="./data/estimated-power.txt", help="File to keep estimated power")
    parser.add_argument("-rt", "--measured-rt", default="./data/real-rt.txt", help="File to keep measured response time")
    parser.add_argument("-trt", "--measured-tail-rt", default="./data/tail-rt.txt", help="File to keep measured tail response times")
    parser.add_argument("-frt", "--filtered-rt", default="./data/filtered-rt.txt", help="File to keep filtered response time")
    parser.add_argument("-lf", "--log-file", default="./data/log-file.txt", help="File to keep interested log file columns")
    parser.add_argument("-ev", "--error-value", default="./data/error-value.txt", help="File to keep error value")
    parser.add_argument("-dp", "--drop-percent", default="./data/drop-percentage.txt", help="File to keep percentage of dropped requests")
    parser.add_argument("-er", "--est-number-of-request", default="./data/est-number-of-request.txt", help="File to keep estimated number of request")
    parser.add_argument("-pt", "--p-terms", default="./data/p-terms.txt", help="File to keep p terms")
    parser.add_argument("-it", "--i-terms", default="./data/i-terms.txt", help="File to keep i terms")
    parser.add_argument("-op", "--operating-points", default="./data/operating-points.txt", help="File to keep operating points")
    parser.add_argument("-in", "--integrator", default="./data/integrator.txt", help="File to keep integrator value")
    parser.add_argument("-is", "--integral-switch-on-off", default="./data/integral-switch-on-off.txt", help="File to keep integrator switch on/off value")
    parser.add_argument("-ac", "--allocated-number-of-core", default="./data/integral-switch-on-off.txt", help="File to keep integrator switch on/off value")
    parser.add_argument("-rac", "--reactively-allocated-number-of-core", default="./data/integral-switch-on-off.txt", help="File to keep integrator switch on/off value")
    parser.add_argument("-pac", "--proactively-allocated-number-of-core", default="./data/integral-switch-on-off.txt", help="File to keep integrator switch on/off value")
    parser.add_argument("-sp", "--measured-server-power", default="./data/measured_server_power.txt", help="File to measured server power")
    parser.add_argument("-cu", "--cpu-utilization", default="./data/cpu_utilization.txt", help="File to keep cpu utilization")
    parser.add_argument("-sr", "--service-rate", default="./data/service-rate.txt", help="File to keep service rate")
    parser.add_argument("-cf", "--cpu-frequency", default="./data/cpu_frequency.txt", help="File to keep cpu frequency")
    parser.add_argument("-bfr", "--best-fit-request-rate", default="./data/best_fit_request_rate.txt", help="File to best fit request rate estimation")
    parser.add_argument("-bfc", "--best-fit-cpu-util", default="./data/best_fit_cpu_util.txt", help="File to keep best fit cpu util")
    parser.add_argument("-tbi", "--to-be-increased-core", default="./data/to_be_increased.txt", help="File to keep to be increased core estimation")
    parser.add_argument("-tbd", "--to-be-decreased-core", default="./data/to_be_decreased.txt", help="File to keep to be decreased core estimation")

    args = parser.parse_args()

    f_allocated_power_data = args.allocated_power           # File for allocated power data
    f_estimated_power_data = args.estimated_power           # File for estimated power data
    f_measured_rt = args.measured_rt                        # File for measured response time
    f_tail_rt = args.measured_tail_rt                       # File for tail response time
    f_filtered_rt = args.filtered_rt                        # File for filtered response time
    f_log_file = args.log_file                              # File for interested apache log file columns
    f_error_value = args.error_value                        # File for controller input/error input
    f_drop_percent = args.drop_percent                      # File for keeping drop percentage
    f_est_number_of_request = args.est_number_of_request    # File for keeping estimating number of requests
    f_p_terms = args.p_terms                                # File for keeping P terms
    f_i_terms = args.i_terms                                # File for keeping I terms
    f_operating_points = args.operating_points              # File for keeping operating point values
    f_integrator = args.integrator                          # File for keeping integrator
    f_integral_switch_on_off = args.integral_switch_on_off  # File for keeping integral switch on/off
    f_allocated_number_of_core_data = args.allocated_number_of_core  # File for keeping allocated number of core data
    f_reactively_allocated_number_of_core_data = args.reactively_allocated_number_of_core  # File for keeping reactively allocated number of core data
    f_proactively_allocated_number_of_core_data = args.proactively_allocated_number_of_core  # File for keeping proactively allocated number of core data
    f_measured_server_power = args.measured_server_power    # File for keeping measured server power consumption
    f_cpu_util = args.cpu_utilization                       # File for keeping cpu utilization
    f_service_rate = args.service_rate                      # File for keeping service rate data
    f_cpu_freq = args.cpu_frequency                         # File for keeping cpu frequency
    f_rate_best_fit = args.best_fit_request_rate
    f_cpu_util_best_fit = args.best_fit_cpu_util
    f_to_be_increased_core_list = args.to_be_increased_core
    f_to_be_reduced_core_list = args.to_be_decreased_core

    serve(args.host, args.port, args.workers)
