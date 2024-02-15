import grpc
from concurrent import futures
from Utility import Utility
import power_capper_pb2 as pb2
import power_capper_pb2_grpc as pb2_grpc
import argparse
import os
import subprocess

# A class for handling power tools service
class PowerCapper(pb2_grpc.PowerCapperServicer):
    # Implementation of interface method defined in proto file.
    def cap_power(self, request, context):
        print(f"To be capped power at socket(s): {request.power_cap} Watts")
        allocate_power(request.power_cap)
        return pb2.Cap_Output(status=True)


def allocate_power(power_cap_value):
    utility = Utility()

    # proc1 = subprocess.run(['echo', str(int(utility.convert_from_watt_to_microwatt(power_cap_value)))], stdout=subprocess.PIPE)
    proc1 = subprocess.run(['echo', str(int(power_cap_value))], stdout=subprocess.PIPE)
    subprocess.run(['sudo', 'tee', '/sys/class/powercap/intel-rapl/intel-rapl:0/constraint_0_power_limit_uw'], input=proc1.stdout, stdout=subprocess.PIPE)
    subprocess.run(['sudo', 'tee', '/sys/class/powercap/intel-rapl/intel-rapl:1/constraint_0_power_limit_uw'], input=proc1.stdout, stdout=subprocess.PIPE)

    print(f"Power just capped at: {power_cap_value} Watts")

    # os.system(f"echo {utility.convert_from_watt_to_microwatt(power_cap_value)} | sudo tee /sys/class/powercap/intel-rapl/intel-rapl:0/constraint_0_power_limit_uw")
    # os.system(f"echo {utility.convert_from_watt_to_microwatt(power_cap_value)} | sudo tee /sys/class/powercap/intel-rapl/intel-rapl:1/constraint_0_power_limit_uw")


def serve(port, max_workers):
   server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
   pb2_grpc.add_PowerCapperServicer_to_server(PowerCapper(), server)
   server.add_insecure_port(f"[::]:{port}")
   server.start()
   print(f"Power Capper Server started on port {port} with {max_workers} workers.")
   server.wait_for_termination()

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Power Capping Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-p", "--port", type=int, default=8088,
                        help="Network port")
    
    parser.add_argument("-w", "--workers", default=10,
                        type=int, help="Max Number of workers")
    
    parser.add_argument("-e", "--power", default=85000000,
                        type=int, help="Default power")

    args = parser.parse_args()

    allocate_power(args.power)
    print(f"Power is initially capped at {args.power} Watts per socket")

    serve(args.port, args.workers)