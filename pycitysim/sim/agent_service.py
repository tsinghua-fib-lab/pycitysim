from typing import Any, Awaitable, Coroutine, cast

import grpc
from google.protobuf.json_format import ParseDict
from pycityproto.city.agent.v2 import agent_pb2 as agent_pb2
from pycityproto.city.agent.v2 import agent_service_pb2 as agent_service
from pycityproto.city.agent.v2 import agent_service_pb2_grpc as agent_grpc

from ..utils.protobuf import async_parse

__all__ = ["AgentService"]


class AgentService:
    """交通模拟lane服务"""

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = agent_grpc.AgentServiceStub(aio_channel)

    @staticmethod
    def default_agent() -> agent_pb2.Agent:
        """获取agent基本模板

        需要补充的字段有agent.home,agent.schedules,agent.labels

        """
        agent = agent_pb2.Agent(
            attribute=agent_pb2.AgentAttribute(
                type=agent_pb2.AGENT_TYPE_PERSON,
                length=5.0,
                width=2.0,
                max_speed=41.6666666667,
                max_acceleration=3.0,
                max_braking_acceleration=-10.0,
                usual_acceleration=2.0,
                usual_braking_acceleration=-4.5,
            ),
            vehicle_attribute=agent_pb2.VehicleAttribute(
                lane_change_length=10.0, min_gap=1.0
            ),
        )
        return agent

    def GetAgent(
        self, req: agent_service.GetAgentRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | agent_service.GetAgentResponse]:
        """
        获取agent信息

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.agent.v2.GetAgentRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.agent.v2.GetAgentResponse
        """
        if type(req) != agent_service.GetAgentRequest:
            req = ParseDict(req, agent_service.GetAgentRequest())
        res = cast(
            Awaitable[agent_service.GetAgentResponse], self._aio_stub.GetAgent(req)
        )
        return async_parse(res, dict_return)

    def AddAgent(
        self, req: agent_service.AddAgentRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | agent_service.AddAgentResponse]:
        """
        新增agent

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.agent.v2.AddAgentRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.agent.v2.AddAgentResponse
        """
        if type(req) != agent_service.AddAgentRequest:
            req = ParseDict(req, agent_service.AddAgentRequest())
        res = cast(
            Awaitable[agent_service.AddAgentResponse], self._aio_stub.AddAgent(req)
        )
        return async_parse(res, dict_return)

    def SetSchedule(
        self, req: agent_service.SetScheduleRequest | dict, dict_return: bool = True
    ) -> Coroutine[Any, Any, dict[str, Any] | agent_service.SetScheduleResponse]:
        """
        修改agent的schedule

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.agent.v2.SetScheduleRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.agent.v2.SetScheduleResponse
        """
        if type(req) != agent_service.SetScheduleRequest:
            req = ParseDict(req, agent_service.SetScheduleRequest())
        res = cast(
            Awaitable[agent_service.SetScheduleResponse],
            self._aio_stub.SetSchedule(req),
        )
        return async_parse(res, dict_return)

    def GetAgentsByLongLatArea(
        self,
        req: agent_service.GetAgentsByLongLatAreaRequest | dict,
        dict_return: bool = True,
    ) -> Coroutine[
        Any, Any, dict[str, Any] | agent_service.GetAgentsByLongLatAreaResponse
    ]:
        """
        获取特定区域内的agent

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.agent.v2.GetAgentsByLongLatAreaRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.agent.v2.GetAgentsByLongLatAreaResponse
        """
        if type(req) != agent_service.GetAgentsByLongLatAreaRequest:
            req = ParseDict(req, agent_service.GetAgentsByLongLatAreaRequest())
        res = cast(
            Awaitable[agent_service.GetAgentsByLongLatAreaResponse],
            self._aio_stub.GetAgentsByLongLatArea(req),
        )
        return async_parse(res, dict_return)
