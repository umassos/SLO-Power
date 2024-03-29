import grpc
from concurrent import futures
import dynamic_core_allocator_pb2 as pb2
import dynamic_core_allocator_pb2_grpc as pb2_grpc
import argparse
import subprocess

   # A class for handling controller generator service
class DynamicCoreAllocator(pb2_grpc.DynamicCoreAllocatorServicer):
    # Implementation of interface method defined in proto file.
    def allocate_core(self, request, context):
        print(f"To be allocated core: {request.number_of_cores}")
        subprocess.run(['lxc', 'config', 'set', request.domain_name, 'limits.cpu', str(request.number_of_cores)], stdout=subprocess.PIPE)
        print(f"{request.number_of_cores} has been allocated to {request.domain_name}")

        return pb2.Core_Output(status=True)
    

def serve(host, port, max_workers):    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    pb2_grpc.add_DynamicCoreAllocatorServicer_to_server(DynamicCoreAllocator(), server)
    ''' 
    For using the insecure port
    '''
    server.add_insecure_port(f"[::]:{port}")
    # server.add_insecure_port(f"{host}:{port}")
    '''
    For using the secure port
    '''
    # with open("/Users/msavasci/Desktop/key-new.pem", 'rb') as f:
    #     private_key = f.read()
    # with open("/Users/msavasci/Desktop/certificate.pem", 'rb') as f:
    #     certificate_chain = f.read()
    
    # credentials = grpc.ssl_server_credentials( ( (private_key, certificate_chain,), ) )

    # # server.add_secure_port(f"[::]:{port}", credentials)
    # server.add_secure_port(f"{host}:{port}", credentials)
    server.start()
    print(f"Dynamic Core Allocator Server started on port {port} with {max_workers} workers.")
    server.wait_for_termination()
   

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dynamic Core Allocator Server", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-H", "--host", default="0.0.0.0",
                        help="Network host")
    
    parser.add_argument("-p", "--port", type=int, default=8090,
                        help="Network port")
    
    parser.add_argument("-w", "--workers", default=10,
                        type=int, help="Max number of workers")

    parser.add_argument("-d", "--domain", default="mediawiki-51-1",
                        help="Default container")
    
    parser.add_argument("-c", "--cores", default=16,
                        type=int, help="Default number of cores")
    
    args = parser.parse_args()

    subprocess.run(['lxc', 'config', 'set', args.domain, 'limits.cpu', str(args.cores)], stdout=subprocess.PIPE)

    print(f"Container {args.domain} is initialized with {args.cores} cores.")

    serve(args.host, args.port, args.workers)
