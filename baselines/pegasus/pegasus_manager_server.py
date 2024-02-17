import grpc
from concurrent import futures
from Utility import Utility
import power_capper_pb2 as pb2_pwr
import power_capper_pb2_grpc as pb2_pwr_grpc
import container_service_pb2 as pb2_container_service
import container_service_pb2_grpc as pb2_container_service_grpc
import rapl_power_monitor_pb2 as pb2_monitor
import rapl_power_monitor_pb2_grpc as pb2_monitor_grpc
import argparse
import numpy as np
import time
import timeit
import statistics as stat
import subprocess
import pickle
import json
import os


f_allocated_power_data, f_real_rt, f_tail_rt, f_log_file, f_error_value, f_drop_percent, f_est_number_of_request, f_measured_server_power, f_cpu_util, f_cpu_freq = "", "", "", "", "", "", "", "", "", ""

# Instantiate Utility class to use utilities such as 'converting from second to millisecond', etc.
my_utility = Utility()

# machines_config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/single_machines.json"
machines_config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/cluster_machines.json"
config_file = "/nfs/obelix/users1/msavasci/PoVerScaler/system-implementation/power_manager_config.json"
info_log_file = "/nfs/obelix/raid2/msavasci/SLO-Power-Experiments/SLO-Power/Experiment-422/info_log.txt"


# This method returns [average response time, perct, #req/s, log_data, drop_rate, arrival_rate, service_rate] in this order
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

    # Clean the log file.
    subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)
    
    return response_times, average_rt, perct, request_per_second, log_lines, drop_rate


def write_to_file( allocated_power_data, measured_response_time_data, tail_response_time_data, error_data, drop_percentage, estimated_number_of_request_data, log_data,  measured_server_power_data, cpu_util_data, cpu_freq_data):
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
    
    with open(f_measured_server_power, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]}),' for tup in measured_server_power_data))

    with open(f_cpu_util, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]},{tup[3]}),' for tup in cpu_util_data))

    with open(f_cpu_freq, 'a', encoding='utf-8') as filehandle:
        filehandle.write(''.join(f'({tup[0]},{tup[1]},{tup[2]}),' for tup in cpu_freq_data))
    
    with open(f_log_file, 'wb') as filehandle:
        pickle.dump(log_data, filehandle)


def run_power_allocator(host, port, allocated_power):
    with grpc.insecure_channel(f'{host}:{port}') as channel:
        stub = pb2_pwr_grpc.PowerCapperStub(channel)
        response = stub.cap_power( pb2_pwr.Cap_Input( power_cap=int(my_utility.convert_from_watt_to_microwatt(allocated_power)) ) )

        return response.status
    

def retrieve_cpu_freq_information(machine_ip, machine_port, container_name):
    with grpc.insecure_channel(f'{machine_ip}:{machine_port}') as channel:
        stub = pb2_container_service_grpc.ContainerServiceStub(channel)
        s = stub.retrieve_cpu_freq_information( pb2_container_service.Container_Service_Input(domain_name=container_name))
        return s.cpu_freq
        

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
    hashed_object = hash(modify_time)
    return hashed_object

def run_manager(power_min_limit, power_max_limit, sampling_time, application_sub_path, ref_input, log_file):
    ''' To keep configuration variables '''
    config_dict = {}

    with open(config_file, "r") as f:
        config_dict = json.load(f)

    recording_frequency = config_dict["system_configs"]["recording_frequency"]
    number_of_cpu_sockets = config_dict["system_configs"]["number_of_cpu_sockets"]
    rt_percentile = config_dict["system_configs"]["rt_percentile"]

    real_response_time_data, tail_response_time, error_data, estimated_number_of_request_data, drop_percentage, allocated_power_data,= [], [], [], [], [], []
    
    measured_server_power, cpu_util, cpu_freq = [], [], []

    log_records = {}

    with open(machines_config_file) as f:
        machines = json.load(f)

    print(f"Controller min power limit for node: {power_min_limit}")
    print(f"Controller max power limit for node: {power_max_limit}")
    print(f"Target response time of the application: {ref_input} ms")

    iteration_counter = 0

    prev_controller_output = power_max_limit

    rt_time_window = []

    initial_wait_flag = True

    print(f"Ref_input: {ref_input}")

    time_window_duration = 30

    while True:
        prev_hash = hash_of_file(log_file)
        
        time.sleep(1)

        if prev_hash != hash_of_file(log_file):
            break

    time.sleep(10)

    recording_start_time = timeit.default_timer()

    initial_time = time.time()

    subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)

    print("HAProxy log file is cleared for the initialization purpose.")

    while True:
        # if initial_wait_flag == True:
        #     # time.sleep(sampling_time * max(cpu_util_window_size, request_rate_window_size))
        #     time.sleep(sampling_time * 2)
        #     subprocess.run(['sudo', 'truncate', '-s', '0', log_file], stdout=subprocess.PIPE)
        #     initial_time = time.time()
        #     initial_wait_flag = False

        if timeit.default_timer() - recording_start_time >= recording_frequency:
            print("Recording to log file...")
            write_to_file(allocated_power_data, real_response_time_data, tail_response_time, error_data, drop_percentage, estimated_number_of_request_data, log_records, measured_server_power, cpu_util, cpu_freq)

            real_response_time_data, tail_response_time, error_data, estimated_number_of_request_data, drop_percentage, allocated_power_data = [], [], [], [], [], []
    
            measured_server_power, cpu_util, cpu_freq = [], [], []

            log_records = {}

            recording_start_time = timeit.default_timer()

        time.sleep(sampling_time)

        rt_times_list, mean_response_time, percent_rt, estimated_number_of_request, log, drop = sample_log(log_file, rt_percentile, sampling_time)

        if mean_response_time <= 1:
            print(f"No (logical) response time has been read; therefore, wait for {sampling_time} seconds.")
            continue

        iteration_counter += 1

        print(f"Iteration: {iteration_counter}, Estimated number of request: {estimated_number_of_request}, Average response time: {mean_response_time}, Tail response time: {percent_rt}")
        # Adding average response time into the list
        real_response_time_data.append((iteration_counter, mean_response_time))
        # Adding tail response time into the list
        tail_response_time.append((iteration_counter, percent_rt))
        # Adding estimated number of request value into the list
        estimated_number_of_request_data.append((iteration_counter, estimated_number_of_request))        
        # Adding drop percentage into the list.
        drop_percentage.append((iteration_counter, drop))
        # Adding log data info into the list.
        log_records[iteration_counter] = log

        curr_error = ref_input - percent_rt
        # Add error value into list.
        error_data.append((iteration_counter, curr_error))

        # Retrieve power consumption information of nodes.
        for mac in machines["machines"]["power_monitor"]:
            tmp_pow = retrieve_cpu_power_consumption(mac["ip"], mac["port"])
            measured_server_power.append((iteration_counter, str(mac["ip"]), tmp_pow))

        # Retrieve cpu frequency information of nodes and cpu utilization information of containers.
        for mac in machines["machines"]["container_service"]:
            cpu_freq.append((iteration_counter, str(mac["ip"]), retrieve_cpu_freq_information(mac["ip"], mac["port"], "")))

            for c1 in mac["container_name"]:
                tmp_cpu_util = retrieve_container_cpu_usage_information(mac["ip"], mac["port"], c1)
                cpu_util.append((iteration_counter, str(mac["ip"]), str(c1), tmp_cpu_util))

        rt_time_window.append(np.percentile(rt_times_list, rt_percentile))

        if time.time() - initial_time >= time_window_duration:
            if stat.mean(rt_time_window) > ref_input:
                curr_controller_output = power_max_limit
                prev_controller_output = power_max_limit

                for m1 in machines["machines"]["power_allocator"]:
                    step1_output = run_power_allocator(m1["ip"], m1["port"], curr_controller_output)    

                    if step1_output == True:
                        print(f"Power has been set to {curr_controller_output} Watts on {m1['ip']}.")

                    else:
                        with open(info_log_file, "a") as f:
                            f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_controller_output} Watts on {m1['ip']}. Thus, old power value stays in effect!\n")

                # writeToFile(estimatedControllerOutput * len(list(ipToMachineNames.keys())), responseTimeData, dropPercentage, estimatedNumberOfRequest, logData)
                allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_controller_output))))

                write_to_file(allocated_power_data, real_response_time_data, tail_response_time, error_data, drop_percentage, estimated_number_of_request_data, log_records, measured_server_power, cpu_util, cpu_freq)

                sub_time = time.time()

                while time.time() - sub_time <= time_window_duration:
                    time.sleep(sampling_time)
                    
                    real_response_time_data, tail_response_time, error_data, estimated_number_of_request_data, drop_percentage, allocated_power_data = [], [], [], [], [], []
    
                    measured_server_power, cpu_util, cpu_freq = [], [], []

                    log_records = {}
                    
                    rt_times_list, mean_response_time, percent_rt, estimated_number_of_request, log, drop = sample_log(log_file, rt_percentile, sampling_time)

                    if mean_response_time <= 1:
                        print(f"No (logical) response time has been read; therefore, wait for {sampling_time} seconds.")
                        continue

                    iteration_counter += 1

                    rt_time_window.append(stat.mean(rt_times_list))

                    # Adding average response time into the list
                    real_response_time_data.append((iteration_counter, mean_response_time))
                    # Adding tail response time into the list
                    tail_response_time.append((iteration_counter, percent_rt))
                    # Adding estimated number of request value into the list
                    estimated_number_of_request_data.append((iteration_counter, estimated_number_of_request))        
                    # Adding drop percentage into the list.
                    drop_percentage.append((iteration_counter, drop))
                    # Adding log data info into the list.
                    log_records[iteration_counter] = log

                    # curr_error = float("{:.2f}".format(my_utility.convert_from_millisecond_to_second(ref_input - mean_response_time)))
                    # curr_error = ref_input - percent_rt - slo_guard
                    curr_error = ref_input - percent_rt
                    # Add error value into list.
                    error_data.append((iteration_counter, curr_error))

                    allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_controller_output))))

                    # Retrieve power consumption information of nodes.
                    for mac in machines["machines"]["power_monitor"]:
                        tmp_pow = retrieve_cpu_power_consumption(mac["ip"], mac["port"])
                        measured_server_power.append((iteration_counter, str(mac["ip"]), tmp_pow))

                    # Retrieve cpu frequency information of nodes and cpu utilization information of containers.
                    for mac in machines["machines"]["container_service"]:
                        cpu_freq.append((iteration_counter, str(mac["ip"]), retrieve_cpu_freq_information(mac["ip"], mac["port"], "")))

                        for c1 in mac["container_name"]:
                            tmp_cpu_util = retrieve_container_cpu_usage_information(mac["ip"], mac["port"], c1)
                            cpu_util.append((iteration_counter, str(mac["ip"]), str(c1), tmp_cpu_util))

                    write_to_file(allocated_power_data, real_response_time_data, tail_response_time, error_data, drop_percentage, estimated_number_of_request_data, log_records, measured_server_power, cpu_util, cpu_freq)

                rt_time_window.clear()
                initial_time = time.time()
                continue

        if percent_rt > (1.35 * ref_input):
            curr_controller_output = power_max_limit
            prev_controller_output = power_max_limit

        elif percent_rt > ref_input:
            curr_controller_output = prev_controller_output + (prev_controller_output * 0.07)

            if curr_controller_output > power_max_limit:
                curr_controller_output = power_max_limit
                prev_controller_output = power_max_limit

            else:
                prev_controller_output += (prev_controller_output * 0.07)

        elif percent_rt >= (0.85 * ref_input) and percent_rt <= ref_input:
            curr_controller_output = prev_controller_output

        elif percent_rt < (0.85 * ref_input):
            curr_controller_output = prev_controller_output - (prev_controller_output * 0.01)

            if curr_controller_output < power_min_limit:
                curr_controller_output = power_min_limit
                prev_controller_output = power_min_limit

            else:
                prev_controller_output -= (prev_controller_output * 0.01)

        elif percent_rt < (0.6 * ref_input):
            curr_controller_output = prev_controller_output - (prev_controller_output * 0.03)

            if curr_controller_output < power_min_limit:
                curr_controller_output = power_min_limit
                prev_controller_output = power_min_limit

            else:
                prev_controller_output -= (prev_controller_output * 0.03)

        for m1 in machines["machines"]["power_allocator"]:
            step1_output = run_power_allocator(m1["ip"], m1["port"], curr_controller_output)    

            if step1_output == True:
                print(f"Power has been set to {curr_controller_output} Watts on {m1['ip']}.")

            else:
                with open(info_log_file, "a") as f:
                    f.write(f"Iteration: {iteration_counter} - Power could not been set to {curr_controller_output} Watts on {m1['ip']}. Thus, old power value stays in effect!\n")

        allocated_power_data.append((iteration_counter, int(my_utility.convert_from_watt_to_microwatt(curr_controller_output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Power Manager Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-H", "--host", default="localhost",
                        help="Network host")
    parser.add_argument("-p", "--port", type=int, default=8090,
                        help="Network port")
    parser.add_argument("-w", "--workers", default=10,
                        type=int, help="Max Number of workers")
    
    parser.add_argument("-ap", "--allocated-power", default="./data/allocated-power.txt", help="File to keep allocated power")
    parser.add_argument("-rt", "--measured-rt", default="./data/real-rt.txt", help="File to keep measured response time")
    parser.add_argument("-trt", "--measured-tail-rt", default="./data/tail-rt.txt", help="File to keep measured tail response times")
    parser.add_argument("-lf", "--log-file", default="./data/log-file.txt", help="File to keep interested log file columns")
    parser.add_argument("-ev", "--error-value", default="./data/error-value.txt", help="File to keep error value")
    parser.add_argument("-dp", "--drop-percent", default="./data/drop-percentage.txt", help="File to keep percentage of dropped requests")
    parser.add_argument("-er", "--est-number-of-request", default="./data/est-number-of-request.txt", help="File to keep estimated number of request")
    parser.add_argument("-sp", "--measured-server-power", default="./data/measured_server_power.txt", help="File to measured server power")
    parser.add_argument("-cu", "--cpu-utilization", default="./data/cpu_utilization.txt", help="File to keep cpu utilization")
    parser.add_argument("-cf", "--cpu-frequency", default="./data/cpu_frequency.txt", help="File to keep cpu frequency")

    args = parser.parse_args()

    f_allocated_power_data = args.allocated_power           # File for allocated power data
    f_measured_rt = args.measured_rt                        # File for measured response time
    f_tail_rt = args.measured_tail_rt                       # File for tail response time
    f_log_file = args.log_file                              # File for interested apache log file columns
    f_error_value = args.error_value                        # File for controller input/error input
    f_drop_percent = args.drop_percent                      # File for keeping drop percentage
    f_est_number_of_request = args.est_number_of_request    # File for keeping estimating number of requests
    f_measured_server_power = args.measured_server_power    # File for keeping measured server power consumption
    f_cpu_util = args.cpu_utilization                       # File for keeping cpu utilization
    f_cpu_freq = args.cpu_frequency                         # File for keeping cpu frequency

    run_manager(30, 46, 2, "/gw", 150, "/var/log/haproxy.log")
