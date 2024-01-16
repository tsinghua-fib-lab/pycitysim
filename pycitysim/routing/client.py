from typing import Any, Awaitable, Coroutine, cast, Union, Dict

import grpc
from google.protobuf.json_format import ParseDict
from pycityproto.city.routing.v2 import routing_service_pb2 as routing_service
from pycityproto.city.routing.v2 import routing_service_pb2_grpc as routing_grpc

from ..utils.protobuf import async_parse

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

    def GetRoute(
        self,
        req: Union[routing_service.GetRouteRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[Any, Any, Union[Dict[str, Any], routing_service.GetRouteResponse]]:
        """
        请求导航

        Args:
        - req (routing_service.GetRouteRequest): https://cityproto.sim.fiblab.net/#city.routing.v2.GetRouteRequest
        - dict_return (bool, optional): 是否返回dict类型的结果. Defaults to True.

        Returns:
        - https://cityproto.sim.fiblab.net/#city.routing.v2.GetRouteResponse
        """
        if type(req) != routing_service.GetRouteRequest:
            req = ParseDict(req, routing_service.GetRouteRequest())
        res = cast(
            Awaitable[routing_service.GetRouteResponse], self._aio_stub.GetRoute(req)
        )
        return async_parse(res, dict_return)
