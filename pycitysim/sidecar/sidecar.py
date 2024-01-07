import logging
from time import sleep
from typing import cast

import grpc
from pycityproto.city.sync.v1 import sync_service_pb2 as sync_service
from pycityproto.city.sync.v1 import sync_service_pb2_grpc as sync_grpc

__all__ = ["OnlyClientSidecar"]


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

    def wait_url(self, name: str) -> str:
        """
        获取服务的uri

        Args:
        - name (str): 服务的注册名

        Returns:
        - str: 服务的url
        """
        while True:
            try:
                resp = cast(
                    sync_service.GetURLResponse,
                    self._sync_stub.GetURL(sync_service.GetURLRequest(name=name)),
                )
                url = resp.url
                break
            except grpc.RpcError as e:
                logging.warning("get uri failed, retrying..., %s", e)
                sleep(1)

        logging.debug("get uri: %s for name=%s", url, name)
        return url

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

    def notify_step_ready(self):
        """通知prepare阶段已完成"""
        ...
