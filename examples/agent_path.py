import asyncio
from typing import cast
import json
from pycitysim.routing import RoutingClient
from pycitysim.map import Map
from pycitysim.utils import wrap_feature_collection


async def main():
    # 初始化地图
    # Initialize the map
    m = Map(
        mongo_uri="mongodb://username:password@url:port/",
        mongo_db="opencity",
        mongo_coll="map_beijing",
        cache_dir="./cache",
    )
    # 初始化路由客户端
    # Initialize the routing client
    # 服务端启动：https://tsinghuafiblab.yuque.com/flnu7r/qtl7iz/btpk3cdu93r2hwq6#Tk8wk
    client = RoutingClient("localhost:52101")
    req = {
        "type": 2,
        "start": {"aoi_position": {"aoi_id": 500000000}},
        "end": {"aoi_position": {"aoi_id": 500000001}},
    }
    # req = {
    #     "type": 1,  # 1 开车 2 走路
    #     "start": {"aoi_position": {"aoi_id": 500000000}},  # 指定起点是AOI，ID为xxx
    #     "end": {
    #         "lane_position": {"lane_id": 100, "s": 1.2}
    #     },  # 指定终点是Lane，ID为xxx，s为Lane上的位置
    # }

    # 请求导航
    # Request for routing
    res = await client.GetRoute(req)
    res = cast(dict, res)
    # 返回结果导出为GeoJSON
    # Export the result as GeoJSON
    feature = m.export_route_as_geojson(req, res, {"PathKey1": "something"})
    eta = m.estimate_route_time(req, res)
    print("eta:", eta)
    fc = wrap_feature_collection([feature], "填写FeatureCollection的name")
    with open("output.geojson", "w") as f:
        json.dump(fc, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
