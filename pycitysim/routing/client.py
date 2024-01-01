import grpc

from google.protobuf.json_format import ParseDict

from pycityproto.city.routing.v2 import (
    routing_service_pb2 as routing_service,
    routing_service_pb2_grpc as routing_grpc,
)
from ..utils.protobuf import async_parser

__all__ = [
    "RoutingClient",
]


class RoutingClient:
    """Routing服务的client端"""

    def __init__(self, server_address: str):
        """RoutingClient的构造函数

        Args:
        - server_address (str): routing服务器地址
        """
        aio_channel = grpc.aio.insecure_channel(server_address)
        self._aio_stub = routing_grpc.RoutingServiceStub(aio_channel)

    def GetRoute(self, req, dict_return: bool = True):
        """
        请求导航

        Args:
        - req (routing_service.GetRouteRequest): 请求导航的参数
        - dict_return (bool, optional): 是否返回dict类型的结果. Defaults to True.

        Returns:
        - Any: 如果dict_return为True, 返回dict类型的结果, 否则返回protobuf类型的结果
        """
        if type(req) != routing_service.GetRouteRequest:
            req = ParseDict(req, routing_service.GetRouteRequest())
        res = self._aio_stub.GetRoute(req)
        return async_parser(res, dict_return)
