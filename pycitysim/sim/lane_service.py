from typing import Any, Awaitable, Coroutine, cast

import grpc
from google.protobuf.json_format import ParseDict
from pycityproto.city.map.v2 import lane_service_pb2 as lane_service
from pycityproto.city.map.v2 import lane_service_pb2_grpc as lane_grpc

from ..utils.protobuf import async_parser

__all__ = ["LaneService"]


class LaneService:
    """交通模拟lane服务"""

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = lane_grpc.LaneServiceStub(aio_channel)

    def GetLane(
        self, req: lane_service.GetLaneRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | lane_service.GetLaneResponse]:
        """
        获取Lane的信息

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.map.v2.GetLaneRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.map.v2.GetLaneResponse
        """
        if type(req) != lane_service.GetLaneRequest:
            req = ParseDict(req, lane_service.GetLaneRequest())
        res = cast(Awaitable[lane_service.GetLaneResponse], self._aio_stub.GetLane(req))
        return async_parser(res, dict_return)

    def SetLaneMaxV(
        self, req: lane_service.SetLaneMaxVRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | lane_service.SetLaneMaxVResponse]:
        """
        设置Lane的最大速度（限速）

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.map.v2.SetLaneMaxVRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.map.v2.SetLaneMaxVResponse
        """
        if type(req) != lane_service.SetLaneMaxVRequest:
            req = ParseDict(req, lane_service.SetLaneMaxVRequest())
        res = cast(
            Awaitable[lane_service.SetLaneMaxVResponse], self._aio_stub.SetLaneMaxV(req)
        )
        return async_parser(res, dict_return)
