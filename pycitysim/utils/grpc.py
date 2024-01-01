from typing import Callable, Optional
import logging
import grpc

__all__ = ["ClientInterceptor"]


class ClientInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    def __init__(self, precondition: Optional[Callable] = None):
        self._precondition = precondition

    def intercept_unary_unary(self, continuation, client_call_details, request):
        if self._precondition is not None:
            logging.debug("precondition")
            self._precondition()
        return continuation(client_call_details, request)
