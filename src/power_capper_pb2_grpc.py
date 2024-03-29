# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import power_capper_pb2 as power__capper__pb2


class PowerCapperStub(object):
    """The Power capper service definition.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.cap_power = channel.unary_unary(
                '/PowerCapper/cap_power',
                request_serializer=power__capper__pb2.Cap_Input.SerializeToString,
                response_deserializer=power__capper__pb2.Cap_Output.FromString,
                )


class PowerCapperServicer(object):
    """The Power capper service definition.
    """

    def cap_power(self, request, context):
        """Sends a capping instruction
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_PowerCapperServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'cap_power': grpc.unary_unary_rpc_method_handler(
                    servicer.cap_power,
                    request_deserializer=power__capper__pb2.Cap_Input.FromString,
                    response_serializer=power__capper__pb2.Cap_Output.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'PowerCapper', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class PowerCapper(object):
    """The Power capper service definition.
    """

    @staticmethod
    def cap_power(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/PowerCapper/cap_power',
            power__capper__pb2.Cap_Input.SerializeToString,
            power__capper__pb2.Cap_Output.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
