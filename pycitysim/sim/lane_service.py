from typing import Awaitable, Coroutine, cast
import grpc

from google.protobuf.json_format import ParseDict

from pycityproto.city.traffic.interaction.lane.v1 import (
    lane_service_pb2 as lane_service,
    lane_service_pb2_grpc as lane_grpc,
)
from traitlets import Any
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
        gRPC接口：
        - https://cityproto.sim.fiblab.net/#city.traffic.interaction.lane.v1.GetLaneRequest
        - https://cityproto.sim.fiblab.net/#city.traffic.interaction.lane.v1.GetLaneResponse
        """
        if type(req) != lane_service.GetLaneRequest:
            req = ParseDict(req, lane_service.GetLaneRequest())
        res = cast(Awaitable[lane_service.GetLaneResponse], self._aio_stub.GetLane(req))
        return async_parser(res, dict_return)

    def SetMaxV(
        self, req: lane_service.SetMaxVRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | lane_service.SetMaxVResponse]:
        """
        gRPC接口：
        - https://cityproto.sim.fiblab.net/#city.traffic.interaction.lane.v1.SetMaxVRequest
        - https://cityproto.sim.fiblab.net/#city.traffic.interaction.lane.v1.SetMaxVResponse
        """
        if type(req) != lane_service.SetMaxVRequest:
            req = ParseDict(req, lane_service.SetMaxVRequest())
        res = cast(Awaitable[lane_service.SetMaxVResponse], self._aio_stub.SetMaxV(req))
        return async_parser(res, dict_return)
