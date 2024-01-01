import grpc

from ..sidecar import OnlyClientSidecar
from .lane_service import LaneService
from .agent_service import AgentService
from .aoi_service import AoiService
from .road_service import RoadService
from .social_service import SocialService

__all__ = ["CityClient"]


class CityClient:
    """模拟器接口"""

    NAME = "traffic"

    def __init__(self, sidecar: OnlyClientSidecar, name: str = NAME):
        """
        Args:
        - server_address (str): 模拟器server的地址
        """
        uri = sidecar.get_service_uri(name)
        interceptor = sidecar.add_watch_api_status(name)
        aio_channel = grpc.aio.insecure_channel(
            uri,
            interceptors=[interceptor],  # type: ignore
        )
        self._lane_service = LaneService(aio_channel)
        self._agent_service = AgentService(aio_channel)
        self._aoi_service = AoiService(aio_channel)
        self._road_service = RoadService(aio_channel)
        self._social_service = SocialService(aio_channel)

    @property
    def lane_service(self):
        """模拟器lane服务子模块"""
        return self._lane_service

    @property
    def agent_service(self):
        """模拟器智能体服务子模块"""
        return self._agent_service

    @property
    def aoi_service(self):
        """模拟器AOI服务子模块"""
        return self._aoi_service

    @property
    def road_service(self):
        """模拟器road服务子模块"""
        return self._road_service

    @property
    def social_service(self):
        """模拟器social服务子模块"""
        return self._social_service
