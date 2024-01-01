from typing import Awaitable, cast, Coroutine, Any
import grpc

from google.protobuf.json_format import ParseDict

from pycityproto.city.social.v1 import (
    social_service_pb2 as social_service,
    social_service_pb2_grpc as social_grpc,
)
from ..utils.protobuf import async_parser

__all__ = ["SocialService"]


class SocialService:
    """城市模拟社交服务"""

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = social_grpc.SocialServiceStub(aio_channel)

    def Send(
        self, req: social_service.SendRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | social_service.SendResponse]:
        """
        gRPC接口：
        - https://cityproto.sim.fiblab.net/#city.social.v1.SendRequest
        - https://cityproto.sim.fiblab.net/#city.social.v1.SendResponse
        """
        if type(req) != social_service.SendRequest:
            req = ParseDict(req, social_service.SendRequest())
        res = cast(Awaitable[social_service.SendResponse], self._aio_stub.Send(req))
        return async_parser(res, dict_return)

    def Receive(
        self, req: social_service.ReceiveRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | social_service.ReceiveResponse]:
        """
        gRPC接口：
        - https://cityproto.sim.fiblab.net/#city.social.v1.ReceiveRequest
        - https://cityproto.sim.fiblab.net/#city.social.v1.ReceiveResponse
        """
        if type(req) != social_service.ReceiveRequest:
            req = ParseDict(req, social_service.ReceiveRequest())
        res = cast(
            Awaitable[social_service.ReceiveResponse], self._aio_stub.Receive(req)
        )
        return async_parser(res, dict_return)
