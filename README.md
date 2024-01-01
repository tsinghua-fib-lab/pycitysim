# pycitysim

protos 中接口的 python 客户端实现

## 安装

```shell
pip install pycitysim --extra-index-url https://__token__:glpat-fq6C-NTr45Z_Te4BV4kC@git.fiblab.net/api/v4/projects/88/packages/pypi/simple
```

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

## 内容

- pycitysim.sim: 模拟器 server 的接口
- pycitysim.map: 地图接口
- pycitysim.routing: 导航 server 的接口
- pycitysim.streetview: 街景接口
- pycitysim.urbankg: 城市知识图谱接口

## 功能

- 模拟器控制（steps）
- 模拟器上 agent 动态信息查询与修改
- 从 mongo 上拉取地图
- 连接导航 server 以计算路由
