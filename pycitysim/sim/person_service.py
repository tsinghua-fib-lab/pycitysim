from typing import Any, Awaitable, Coroutine, cast, Union, Dict
import warnings

import grpc
from google.protobuf.json_format import ParseDict
from pycityproto.city.person.v1 import person_pb2 as person_pb2
from pycityproto.city.person.v1 import person_service_pb2 as person_service
from pycityproto.city.person.v1 import person_service_pb2_grpc as person_grpc

from ..utils.protobuf import async_parse

__all__ = ["PersonService"]


class PersonService:
    """
    交通模拟person服务
    Traffic simulation person service
    """

    def __init__(self, aio_channel: grpc.aio.Channel):
        self._aio_stub = person_grpc.PersonServiceStub(aio_channel)

    @staticmethod
    def default_agent() -> person_pb2.Person:
        warnings.warn(
            "default_agent is deprecated, use default_person instead",
            DeprecationWarning,
        )
        return PersonService.default_person()

    @staticmethod
    def default_person() -> person_pb2.Person:
        """
        获取person基本模板
        Get person basic template

        需要补充的字段有person.home,person.schedules,person.labels
        The fields that need to be supplemented are person.home, person.schedules, person.labels
        """
        person = person_pb2.Person(
            attribute=person_pb2.PersonAttribute(
                length=5.0,
                width=2.0,
                max_speed=41.6666666667,
                max_acceleration=3.0,
                max_braking_acceleration=-10.0,
                usual_acceleration=2.0,
                usual_braking_acceleration=-4.5,
            ),
            vehicle_attribute=person_pb2.VehicleAttribute(
                lane_change_length=10.0, min_gap=1.0
            ),
        )
        return person

    def GetPerson(
        self,
        req: Union[person_service.GetPersonRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[Any, Any, Union[Dict[str, Any], person_service.GetPersonResponse]]:
        """
        获取person信息
        Get person information

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.person.1.GetPersonRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.person.1.GetPersonResponse
        """
        if type(req) != person_service.GetPersonRequest:
            req = ParseDict(req, person_service.GetPersonRequest())
        res = cast(
            Awaitable[person_service.GetPersonResponse], self._aio_stub.GetPerson(req)
        )
        return async_parse(res, dict_return)

    def AddPerson(
        self,
        req: Union[person_service.AddPersonRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[Any, Any, Union[Dict[str, Any], person_service.AddPersonResponse]]:
        """
        新增person
        Add a new person

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.person.1.AddPersonRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.person.1.AddPersonResponse
        """
        if type(req) != person_service.AddPersonRequest:
            req = ParseDict(req, person_service.AddPersonRequest())
        res = cast(
            Awaitable[person_service.AddPersonResponse], self._aio_stub.AddPerson(req)
        )
        return async_parse(res, dict_return)

    def SetSchedule(
        self,
        req: Union[person_service.SetScheduleRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[Any, Any, Union[Dict[str, Any], person_service.SetScheduleResponse]]:
        """
        修改person的schedule
        set person's schedule

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.person.1.SetScheduleRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.person.1.SetScheduleResponse
        """
        if type(req) != person_service.SetScheduleRequest:
            req = ParseDict(req, person_service.SetScheduleRequest())
        res = cast(
            Awaitable[person_service.SetScheduleResponse],
            self._aio_stub.SetSchedule(req),
        )
        return async_parse(res, dict_return)

    def GetPersonByLongLatBBox(
        self,
        req: Union[person_service.GetPersonByLongLatBBoxRequest, dict],
        dict_return: bool = True,
    ) -> Coroutine[
        Any, Any, Union[Dict[str, Any], person_service.GetPersonByLongLatBBoxResponse]
    ]:
        """
        获取特定区域内的person
        Get persons in a specific region

        Args:
        - req (dict): https://cityproto.sim.fiblab.net/#city.person.1.GetPersonByLongLatBBoxRequest

        Returns:
        - https://cityproto.sim.fiblab.net/#city.person.1.GetPersonByLongLatBBoxResponse
        """
        if type(req) != person_service.GetPersonByLongLatBBoxRequest:
            req = ParseDict(req, person_service.GetPersonByLongLatBBoxRequest())
        res = cast(
            Awaitable[person_service.GetPersonByLongLatBBoxResponse],
            self._aio_stub.GetPersonByLongLatBBox(req),
        )
        return async_parse(res, dict_return)
