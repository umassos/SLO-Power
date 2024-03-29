# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import pegasus_pb2 as pegasus__pb2


class PegasusManagerStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.begin_pegasus_manager = channel.unary_unary(
                '/PegasusManager/begin_pegasus_manager',
                request_serializer=pegasus__pb2.Pegasus_Inputs.SerializeToString,
                response_deserializer=pegasus__pb2.Pegasus_Output.FromString,
                )


class PegasusManagerServicer(object):
    """Missing associated documentation comment in .proto file."""

    def begin_pegasus_manager(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PegasusManagerServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'begin_pegasus_manager': grpc.unary_unary_rpc_method_handler(
                    servicer.begin_pegasus_manager,
                    request_deserializer=pegasus__pb2.Pegasus_Inputs.FromString,
                    response_serializer=pegasus__pb2.Pegasus_Output.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'PegasusManager', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class PegasusManager(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def begin_pegasus_manager(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/PegasusManager/begin_pegasus_manager',
            pegasus__pb2.Pegasus_Inputs.SerializeToString,
            pegasus__pb2.Pegasus_Output.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
