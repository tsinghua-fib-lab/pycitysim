from typing import Any, Awaitable, TypeVar
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict

__all__ = ["async_parser"]

T = TypeVar("T", bound=Message)


async def async_parser(res: Awaitable[T], dict_return: bool) -> dict[str, Any] | T:
    """
    将Protobuf await返回值转换为dict或者原始值
    """
    if dict_return:
        return MessageToDict(
            await res,
            including_default_value_fields=True,
            preserving_proto_field_name=True,
            use_integers_for_enums=True,
        )
    else:
        return await res
