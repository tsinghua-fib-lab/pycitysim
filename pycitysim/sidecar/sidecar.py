from typing import cast
from threading import Lock
from time import sleep
import logging

# import etcd3
# from etcd3.watch import WatchResponse
import grpc

from pycityproto.city.sync.v1 import (
    sync_service_pb2 as sync_service,
    sync_service_pb2_grpc as sync_grpc,
)
from ..utils.grpc import ClientInterceptor

__all__ = ["OnlyClientSidecar"]

API_STATUS_SUFFIX = "/api/status"


class OnlyClientSidecar:
    """
    Sidecar框架服务（仅支持作为客户端，不支持对外提供gRPC服务）
    """

    def __init__(
        self,
        name: str,
        syncer_address: str,
    ):
        """
        Args:
        - name (str): 本服务在etcd上的注册名
        - server_address (str): syncer地址
        - listen_address (str): sidecar监听地址
        """
        self._name = name
        channel = grpc.insecure_channel(syncer_address)
        self._sync_stub = sync_grpc.SyncServiceStub(channel)

        # 获取etcd地址
        res = cast(
            sync_service.GetEtcdResponse,
            self._sync_stub.GetEtcd(sync_service.GetEtcdRequest()),
        )
        etcd_port = res.port
        logging.debug(f"etcd address: {syncer_address.split(':')[0]}:{etcd_port}")
        # self._etcd = etcd3.client(syncer_address.split(":")[0], etcd_port)
        # # self._etcd.put(f"/{name}/uri", listen_address)

        # api status
        self._lock = Lock()
        self._api_statuses = {}  # name -> api status

    def get_service_uri(self, name: str) -> str:
        """
        获取服务的uri

        Args:
        - name (str): 服务的注册名

        Returns:
        - str: 服务的uri
        """
        raise NotImplementedError
        uri = cast(bytes, self._etcd.get(f"/{name}/uri")[0]).decode()
        logging.debug("get uri: %s for name=%s", uri, name)
        return uri

    def add_watch_api_status(self, name: str) -> ClientInterceptor:
        """
        添加对api status的监听

        Args:
        - name: 要监听的服务的注册名

        Returns:
        - ClientInterceptor: 用于发出的gRPC请求的拦截器
        """
        return ClientInterceptor()
        raise NotImplementedError
        key = f"/{name}/{API_STATUS_SUFFIX}"
        with self._lock:
            self._api_statuses[key] = self._etcd.get(key)
        self._etcd.add_watch_callback(key, self._api_status_callback)

        def precondition():
            while True:
                if self._check_api_status(name):
                    return
                sleep(0.01)

        return ClientInterceptor(precondition)

    # def _api_status_callback(self, resp: WatchResponse):
    #     with self._lock:
    #         for event in resp.events:
    #             self._api_statuses[event.key.decode()] = event.value.decode()
    #             logging.debug(f"set {self._api_statuses}")

    def _check_api_status(self, name: str) -> bool:
        """
        检查api状态
        - "0"：不可访问（Syncer在即将给该组件同步响应之前设置为该值）
        - "1"：可以访问，但不能立即获得响应（一般情况下Sidecar会在收到Syncer同步响应后、模拟器完成Prepare前设置为该值，并添加一定的保护措施使得RPC请求被阻塞直到Prepare完成。保护措施的实现是个简单的条件变量通知机制）
        - "2"：可以访问，目前处在Update状态（模拟器进入Update阶段后设置为该值）
        """
        raise NotImplementedError
        with self._lock:
            return self._api_statuses.get(f"/{name}/{API_STATUS_SUFFIX}", "0") != "0"

    def step(self, step: int) -> bool:
        """同步器步进

        Args:
        - step (int): 同步器步进步数

        Returns:
        - close (bool): 是否退出模拟
        """
        request = sync_service.StepRequest(name=self._name, step=step)
        response = self._sync_stub.Step(request)
        return response.close

    def init(self) -> bool:
        """同步器初始化

        Returns:
        - close (bool): 是否退出模拟

        Examples:
        ```python
        close = client.init()
        print(close)
        # > False
        ```
        """
        return self.step(1)

    def close(self) -> bool:
        """同步器关闭

        Returns:
        - close (bool): 是否退出模拟
        """
        return self.step(-1)

    def notify_init_ready(self):
        """通知初始化已完成"""
        ...

    def notify_step_ready(self):
        """通知prepare阶段已完成"""
        ...
