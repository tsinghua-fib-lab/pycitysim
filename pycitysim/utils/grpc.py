import grpc

__all__ = ["create_aio_channel"]


def create_aio_channel(server_address: str, secure: bool = False) -> grpc.aio.Channel:
    """
    创建一个grpc的异步channel
    Create a grpc asynchronous channel

    Args:
    - server_address (str): 服务器地址。server address.
    - secure (bool, optional): 是否使用安全连接. Defaults to False. Whether to use a secure connection. Defaults to False.

    Returns:
    - grpc.aio.Channel: grpc的异步channel。grpc asynchronous channel.
    """
    if server_address.startswith("http://"):
        server_address = server_address.split("//")[1]
        if secure:
            raise ValueError("secure channel must use `https` or not use `http`")
    elif server_address.startswith("https://"):
        server_address = server_address.split("//")[1]
        if not secure:
            secure = True

    if secure:
        return grpc.aio.secure_channel(server_address, grpc.ssl_channel_credentials())
    else:
        return grpc.aio.insecure_channel(server_address)
