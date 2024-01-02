from typing import Awaitable, cast, Coroutine, Any
import grpc

from google.protobuf.json_format import ParseDict

from pycityproto.city.traffic.interaction.road.v1 import (
    road_service_pb2 as road_service,
    road_service_pb2_grpc as road_grpc,
)
from ..utils.protobuf import async_parser

__all__ = ["RoadService"]


class RoadService:
    """交通模拟road服务"""

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = road_grpc.RoadServiceStub(aio_channel)

    def GetRoad(
        self, req: road_service.GetRoadRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | road_service.GetRoadResponse]:
        """
        查询道路信息

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.traffic.interaction.road.v1.GetRoadRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.traffic.interaction.road.v1.GetRoadResponse
        """
        if type(req) != road_service.GetRoadRequest:
            req = ParseDict(req, road_service.GetRoadRequest())
        res = cast(Awaitable[road_service.GetRoadResponse], self._aio_stub.GetRoad(req))
        return async_parser(res, dict_return)
