from typing import Any, Awaitable, Coroutine, cast, Union, Dict

import grpc
from google.protobuf.json_format import ParseDict
from pycityproto.city.event.v2 import event_service_pb2 as event_service
from pycityproto.city.event.v2 import event_service_pb2_grpc as event_grpc

from ..utils.protobuf import async_parse

__all__ = ["EventService"]


class EventService:
    """
    城市模拟事件服务
    City simulation event service
    """

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = event_grpc.EventServiceStub(aio_channel)

    def GetEventsByTopic(
        self,
        req: Union[event_service.GetEventsByTopicRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[
        Any, Any, Union[Dict[str, Any], event_service.GetEventsByTopicResponse]
    ]:
        """
        按照topic查询事件
        Query event by topic

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.event.v2.GetEventsByTopicRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.event.v2.GetEventsByTopicResponse
        """
        if type(req) != event_service.GetEventsByTopicRequest:
            req = ParseDict(req, event_service.GetEventsByTopicRequest())
        res = cast(
            Awaitable[event_service.GetEventsByTopicResponse],
            self._aio_stub.GetEventsByTopic(req),
        )
        return async_parse(res, dict_return)

    def ResolveEvents(
        self,
        req: Union[event_service.ResolveEventsRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[
        Any, Any, Union[Dict[str, Any], event_service.ResolveEventsResponse]
    ]:
        """
        确认事件已被处理
        Confirm that the event has been processed
        
        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.event.v2.ResolveEventsRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.event.v2.ResolveEventsResponse
        """
        if type(req) != event_service.ResolveEventsRequest:
            req = ParseDict(req, event_service.ResolveEventsRequest())
        res = cast(
            Awaitable[event_service.ResolveEventsResponse],
            self._aio_stub.ResolveEvents(req),
        )
        return async_parse(res, dict_return)
