r"""
# pycitysim

City Simulator and OpenCity databases Python SDK

## 安装 Installation

```shell
pip install pycitysim
```

安装 grpcio 的过程中，如果出现：
When installing grpcio, you may encounter the following error:

```
pip install fails with "No such file or directory: 'c++': 'c++'"
```

代表缺少 C++相关依赖。在 Debian 镜像上，执行：
It means that C++ related dependencies are missing. On the Debian image, execute:

```shell
sudo apt install build-essential
```

在 alpine 镜像上，执行：
On the alpine image, execute:

```shell
apk add g++
```

## 主要子库 Sub-packages

- pycitysim.apphub: OpenCity后端交互库。OpenCity backend interaction package.
- pycitysim.map: 地图数据操作库。Map data operation package.
- pycitysim.routing: 路径规划操作库。Routing operation package.
- pycitysim.sateimg: 卫星影像数据下载。Satellite image data download.
- pycitysim.sim: 模拟器gRPC接入客户端。City Simulator gRPC access client.
- pycitysim.streetview: 街景图片操作库。Street view image operation package.
- pycitysim.urbankg: 城市知识图谱访问模块。City knowledge graph access module.

## 示例代码

访问 [examples](https://github.com/tsinghua-fib-lab/pycitysim/-/tree/main/examples?ref_type=heads) 查看示例代码。

"""

from . import map, routing, sidecar, sim, urbankg, utils, apphub, streetview, sateimg

__all__ = [
    "map",
    "routing",
    "sidecar",
    "sim",
    "urbankg",
    "utils",
    "apphub",
    "streetview",
    "sateimg",
]
