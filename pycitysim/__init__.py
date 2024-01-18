r"""
# pycitysim

城市模拟器Python库

## 安装

```shell
pip install pycitysim --extra-index-url https://__token__:********@git.fiblab.net/api/v4/projects/88/packages/pypi/simple
```

其中__token__后的`********`是你的个人访问令牌，可以在 [个人设置](https://git.fiblab.net/-/profile/personal_access_tokens) 页面生成。
此外，FIBLAB提供统一的访问账号，请联系管理员获取。

安装 grpcio 的过程中，如果出现

```
pip install fails with "No such file or directory: 'c++': 'c++'"
```

代表缺少 C++相关依赖。在 Debian 镜像上，执行：

```shell
sudo apt install build-essential
```

在 alpine 镜像上，执行：

```shell
apk add g++
```

## 主要子模块

- pycitysim.map: 模拟器地图数据操作模块
- pycitysim.routing: 模拟器路径规划操作模块
- pycitysim.sim: 模拟器gRPC接入客户端
- pycitysim.streetview: 模拟器街景数据访问模块
- pycitysim.urbankg: 模拟器城市知识图谱访问模块

## 示例代码

访问 [examples](https://git.fiblab.net/sim/pycitysim/-/tree/main/examples?ref_type=heads) 查看示例代码。

"""

from . import map, routing, sidecar, sim, urbankg, utils, apphub

__all__ = [
    "map",
    "routing",
    "sidecar",
    "sim",
    "urbankg",
    "utils",
    "apphub",
]
