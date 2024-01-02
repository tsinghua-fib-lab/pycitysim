from typing import Awaitable, Coroutine, cast
import grpc

from google.protobuf.json_format import ParseDict

from pycityproto.city.traffic.interaction.aoi.v1 import (
    aoi_service_pb2 as aoi_service,
    aoi_service_pb2_grpc as aoi_grpc,
)
from traitlets import Any
from ..utils.protobuf import async_parser

__all__ = ["AoiService"]


class AoiService:
    """aoi服务"""

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = aoi_grpc.AoiServiceStub(aio_channel)

    def GetAoi(
        self, req: aoi_service.GetAoiRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | aoi_service.GetAoiResponse]:
        """
        获取AOI信息

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.traffic.interaction.aoi.v1.GetAoiRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.traffic.interaction.aoi.v1.GetAoiResponse
        """
        if type(req) != aoi_service.GetAoiRequest:
            req = ParseDict(req, aoi_service.GetAoiRequest())
        res = cast(Awaitable[aoi_service.GetAoiResponse], self._aio_stub.GetAoi(req))
        return async_parser(res, dict_return)
