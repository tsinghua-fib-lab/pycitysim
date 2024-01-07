import gc
import os
import pickle
import warnings
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pyproj
import shapely
from geojson import Feature
from google.protobuf.json_format import ParseDict
from pycityproto.city.geo.v2 import geo_pb2
from pycityproto.city.routing.v2 import routing_pb2
from pycityproto.city.routing.v2 import routing_service_pb2 as routing_service
from pymongo import MongoClient
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring

__all__ = ["Map"]


class Map:
    """
    模拟器地图API
    """

    def __init__(
        self,
        mongo_uri: str,
        mongo_db: str,
        mongo_coll: str,
        cache_dir: Optional[str] = None,
    ):
        """
        Args:
        - mongo_uri (str): mongo数据库的uri
        - mongo_db (str): 数据库名
        - mongo_coll (str): 集合名
        - cache_dir (Optional[str]): 缓存目录. Defaults to None.
        """
        if cache_dir is None:
            # 显示runtime warning
            warnings.warn(
                "You are not using cache. "
                "It is recommended to use cache when you are using map data."
            )
        map_data = self._download_map_with_cache(
            mongo_uri, mongo_db, mongo_coll, cache_dir
        )

        self.header: dict = map_data["header"]
        """
        地图元数据，包含如下属性:
        - name (string): 城市道路名称，供标识数据集合的语义
        - date (string): 城市道路数据的创建时间
        - north (float): 道路数据的北边界坐标
        - south (float): 道路数据的南边界坐标
        - east (float): 道路数据的东边界坐标
        - west (float): 道路数据的西边界坐标
        - projection (string): PROJ.4 投影字符串，用以支持xy坐标到其他坐标系的转换
        """

        self.juncs: Dict[int, dict] = map_data["juncs"]
        """
        地图中的路口集合（junction），字典的值包含如下属性:
        - id (int): 路口编号
        - lane_ids (list[int]): 属于该路口的所有车道和人行道编号
        """

        self.lanes: Dict[int, dict] = map_data["lanes"]
        """
        地图中的车道集合（lane），字典的值包含如下属性:
        - id (int): 车道编号
        - type (int): 车道类型 (1:行车|2:步行)
        - turn (int): 转向类型 (1:直行|2:左转|3: 右转|4: 掉头)
        - max_speed (float): 最大速度限制(单位: m/s)
        - length (float): 车道中心线的长度(单位: m)
        - width (float): 车道的宽度(单位: m)
        - center_line (list[XYPosition]): 车道中心线的形状
        - predecessors (list[LaneConnection]): 前驱车道编号和连接类型。对于路口内的车道，最多只有一个前驱车道。对于 LANE_TYPE_DRIVING，连接类型必须是 LANE_CONNECTION_TYPE_TAIL。对于 LANE_TYPE_WALKING，两种连接类型都可能。
        - successors (list[LaneConnection]): 后继车道编号和连接类型。对于路口内的车道，最多只有一个后继车道。对于 LANE_TYPE_DRIVING，连接类型必须是 LANE_CONNECTION_TYPE_HEAD。对于 LANE_TYPE_WALKING，两种连接类型都可能。
        - left_lane_ids (list[int]): 左侧相邻车道的车道编号，从最近到最远排列。
        - right_lane_ids (list[int]): 右侧相邻车道的车道编号，从最近到最远排列。
        - parent_id (int): 车道所属的道路/路口编号。
        - aoi_ids (list[int]): 与车道连接的 AOI 编号。
        - shapely_xy (shapely.geometry.LineString): 车道中心线的形状（xy坐标系）
        - shapely_lnglat (shapely.geometry.LineString): 车道中心线的形状（经纬度坐标系）
        """

        self.roads: Dict[int, dict] = map_data["roads"]
        """
        地图中的道路集合（road），字典的值包含如下属性:
        - id (int): 道路编号
        - lane_ids (list[int]): 道路所包含的车道和人行道编号
        - external["highway"] (string): OSM中的道路等级标签
        - external["name"] (string): 道路名称（不一定有）
        """

        self.aois: Dict[int, dict] = map_data["aois"]
        """
        地图中的AOI集合（aoi），字典的值包含如下属性:
        - id (int): AOI编号
        - positions (list[XYPosition]): 多边形空间范围
        - area (float): 面积(单位: m2)
        - external["population"] (int): worldpop人口
        - driving_positions (list[LanePosition]): 和道路网中行车道的连接点
        - walking_positions (list[LanePosition]): 和道路网中人行道的连接点
        - driving_gates (list[XYPosition]): 和道路网中行车道的连接点对应的AOI边界上的位置
        - walking_gates (list[XYPosition]): 和道路网中人行道的连接点对应的AOI边界上的位置
        - land_use (Optional[int]): 用地类型(5:商服用地|6:工矿仓储用地|7:住宅用地|8:公共管理与公共服务用地|10:交通运输用地|12:其他)
        - poi_ids (list[int]): 包含的POI列表
        - shapely_xy (shapely.geometry.Polygon): AOI的形状（xy坐标系）
        - shapely_lnglat (shapely.geometry.Polygon): AOI的形状（经纬度坐标系）
        """

        self.pois: Dict[int, dict] = map_data["pois"]
        """
        地图中的POI集合（poi），字典的值包含如下属性:
        - id (int): POI编号
        - name (string): POI名称
        - category (string): POI类别编码
        - position (XYPosition): POI位置
        - aoi_id (int): POI所属的AOI编号
        - external["tencent_poi_id"] (string): 腾讯地图的POI编号
        """

        self.pois_with_tencent_id: Dict[str, dict] = {
            poi["external"]["tencent_poi_id"]: poi
            for poi in self.pois.values()
            if "tencent_poi_id" in poi.get("external", {})
        }
        """
        地图中的POI集合，字典的值与self.pois相同，但是key为腾讯地图的POI编号
        """

        self.projector: pyproj.Proj = map_data["projector"]
        """
        采用PROJ.4投影字符串创建的转换器，用以支持xy坐标到WGS84坐标系的转换
        """

        self._poi_tree, self._poi_list = self._build_geo_index()

    def _download_map(self, uri: str, db: str, coll: str) -> Dict[str, Any]:
        client = MongoClient(uri)
        m = list(client[db][coll].find({}))
        header = None
        juncs = {}
        roads = {}
        lanes = {}
        aois = {}
        pois = {}
        for d in m:
            del d["_id"]
            t = d["class"]
            data = d["data"]
            if t == "lane":
                lanes[data["id"]] = data
            elif t == "junction":
                juncs[data["id"]] = data
            elif t == "road":
                roads[data["id"]] = data
            elif t == "aoi":
                aois[data["id"]] = data
            elif t == "poi":
                pois[data["id"]] = data
            elif t == "header":
                header = data
        assert header is not None, "header is None"
        projector = pyproj.Proj(header["projection"])  # type: ignore
        # 处理lane的Geos
        for lane in lanes.values():
            nodes = np.array(
                [[one["x"], one["y"]] for one in lane["center_line"]["nodes"]]
            )
            lane["shapely_xy"] = LineString(nodes)
            lngs, lats = projector(nodes[:, 0], nodes[:, 1], inverse=True)
            lane["shapely_lnglat"] = LineString(list(zip(lngs, lats)))
        # 处理road的Geos和其他属性
        for road in roads.values():
            lane_ids = road["lane_ids"]
            driving_lane_ids = [lid for lid in lane_ids if lanes[lid]["type"] == 1]
            road["driving_lane_ids"] = driving_lane_ids
            center_lane_id = lane_ids[len(driving_lane_ids) // 2]
            center_lane = lanes[center_lane_id]
            road["length"] = center_lane["length"]
            road["max_speed"] = center_lane["max_speed"]
            road["shapely_xy"] = center_lane["shapely_xy"]
            road["shapely_lnglat"] = center_lane["shapely_lnglat"]
        # 处理Aoi的Geos
        for aoi in aois.values():
            if "area" not in aoi:
                # 不是多边形aoi
                aoi["shapely_xy"] = Point(
                    aoi["positions"][0]["x"], aoi["positions"][0]["y"]
                )
            else:
                aoi["shapely_xy"] = Polygon(
                    [(one["x"], one["y"]) for one in aoi["positions"]]
                )
            xys = np.array([[one["x"], one["y"]] for one in aoi["positions"]])
            lngs, lats = projector(xys[:, 0], xys[:, 1], inverse=True)
            lnglat_positions = list(zip(lngs, lats))
            if "area" not in aoi:
                aoi["shapely_lnglat"] = Point(lnglat_positions[0])
            else:
                aoi["shapely_lnglat"] = Polygon(lnglat_positions)
        # 处理Poi的Geos
        for poi in pois.values():
            point = Point(poi["position"]["x"], poi["position"]["y"])
            poi["shapely_xy"] = point
            lng, lat = projector(point.x, point.y, inverse=True)
            poi["shapely_lnglat"] = Point([lng, lat])

        return {
            "header": header,
            "juncs": juncs,
            "roads": roads,
            "lanes": lanes,
            "aois": aois,
            "pois": pois,
            "projector": projector,
        }

    def _download_map_with_cache(
        self, uri: str, db: str, coll: str, cache_dir: Optional[str]
    ) -> Dict[str, Any]:
        if cache_dir is None:
            return self._download_map(uri, db, coll)
        # 如果cache_dir不存在，就创建
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"{db}.{coll}.pkl")  # type: ignore
        if os.path.exists(cache_path):
            gc.disable()
            with open(cache_path, "rb") as f:
                m = pickle.load(f)
            gc.enable()
            return m
        else:
            m = self._download_map(uri, db, coll)
            with open(cache_path, "wb") as f:
                pickle.dump(m, f)
            return m

    def _build_geo_index(self):
        # poi:
        # {
        #     "id": 700000000,
        #     "name": "天翼(互联网手机卖场)",
        #     "category": "131300",
        #     "position": {
        #       "x": 448802.148620172,
        #       "y": 4412128.118718166
        #     },
        #     "aoi_id": 500018954,
        #     "external": {
        #       "tencent_poi_id": "11671067008777180817"
        #     }
        # }
        poi_list = list(self.pois.values())
        tree = shapely.STRtree([poi["shapely_xy"] for poi in poi_list])
        return tree, poi_list

    def _get_lane_s(self, position: geo_pb2.Position, lane_id: int) -> float:
        """
        解算position对应的在lane_id上的s值
        """
        # 处理起点处的截断
        if position.HasField("aoi_position"):
            aoi_id = position.aoi_position.aoi_id
            aoi = self.aois[aoi_id]
            ss = [
                p["s"]
                for p in aoi["walking_positions"] + aoi["driving_positions"]
                if p["lane_id"] == lane_id
            ]
            assert len(ss) == 1, f"lane {lane_id} not found in aoi {aoi_id}"
            return ss[0]
        elif position.HasField("lane_position"):
            return position.lane_position.s
        else:
            assert False, f"position {position} has no valid field"

    def _get_driving_geo(self, road_id: int):
        """
        根据道路ID获取几何信息对应的Lane ID和Lane的几何信息
        """
        road = self.roads[road_id]
        aoi_lane_id = road["driving_lane_ids"][-1]
        geo: LineString = road["shapely_xy"]
        return aoi_lane_id, geo

    def _get_walking_geo(self, segment: routing_pb2.WalkingRouteSegment):
        """
        根据步行路段（导航结果）获取几何信息对应的Lane ID和Lane的几何信息
        """
        lane_id = segment.lane_id
        direction = segment.moving_direction
        geo: LineString = self.lanes[lane_id]["shapely_xy"]
        if direction == routing_pb2.MOVING_DIRECTION_BACKWARD:
            geo: LineString = geo.reverse()
        return lane_id, geo

    def lnglat2xy(self, lng: float, lat: float) -> Tuple[float, float]:
        """经纬度转xy坐标

        Args:
        - lng (float): 经度
        - lat (float): 纬度

        Returns:
        - Tuple[float, float]: xy坐标
        """
        return self.projector(lng, lat)

    def xy2lnglat(self, x: float, y: float) -> Tuple[float, float]:
        """xy坐标转经纬度

        Args:
        - x (float): x坐标
        - y (float): y坐标

        Returns:
        - Tuple[float, float]: 经纬度
        """
        return self.projector(x, y, inverse=True)

    def get_header(self):
        """
        查询header
        """
        return self.header

    def get_aoi(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询AOI

        Args:
        - id (int): AOI id
        - include_unused (bool, optional): 是否包含未使用或无效的AOI属性. Defaults to False.

        Returns:
        - Optional[Any]: AOI（经过复制后的dict）
        """
        doc = self.aois.get(id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            del doc["type"]
            if "external" in doc:
                if "driving_distances" in doc["external"]:
                    del doc["external"]["driving_distances"]
                if "driving_lane_project_point" in doc["external"]:
                    del doc["external"]["driving_lane_project_point"]
                if "walking_distances" in doc["external"]:
                    del doc["external"]["walking_distances"]
                if "walking_lane_project_point" in doc["external"]:
                    del doc["external"]["walking_lane_project_point"]
        return doc

    def get_poi(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询poi

        Args:
        - id (int): poi id
        - include_unused (bool, optional): 是否包含未使用或无效的poi属性. Defaults to False.

        Returns:
        - Optional[Any]: poi（经过复制后的dict）
        """
        doc = self.pois.get(id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            ...
        return doc

    def get_poi_by_tencent_id(
        self, tencent_id: str, include_unused: bool = False
    ) -> Optional[Any]:
        """
        查询poi

        Args:
        - tencent_id (str): poi tencent id
        - include_unused (bool, optional): 是否包含未使用或无效的poi属性. Defaults to False.

        Returns:
        - Optional[Any]: poi（经过复制后的dict）
        """
        doc = self.pois_with_tencent_id.get(tencent_id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            ...
        return doc

    def get_lane(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询lane

        Args:
        - id (int): lane id
        - include_unused (bool, optional): 是否包含未使用或无效的lane属性. Defaults to False.

        Returns:
        - Optional[Any]: lane（经过复制后的dict）
        """
        doc = self.lanes.get(id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            if "left_border_line" in doc:
                del doc["left_border_line"]
            if "right_border_line" in doc:
                del doc["right_border_line"]
            if "overlaps" in doc:
                del doc["overlaps"]
        return doc

    def get_road(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询road

        Args:
        - id (int): road id
        - include_unused (bool, optional): 是否包含未使用或无效的road属性. Defaults to False.

        Returns:
        - Optional[Any]: road（经过复制后的dict）
        """
        doc = self.roads.get(id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            ...
        return doc

    def get_junction(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询junction

        Args:
        - id (int): junction id
        - include_unused (bool, optional): 是否包含未使用或无效的junction属性. Defaults to False.

        Returns:
        - Optional[Any]: junction（经过复制后的dict）
        """
        doc = self.juncs.get(id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            if "external" in doc:
                del doc["external"]
            if "driving_lane_groups" in doc:
                del doc["driving_lane_groups"]
        return doc

    def export_aoi_center_as_geojson(
        self,
        id: int,
        properties: Union[Dict[str, Any], str] = "auto",
    ) -> dict:
        """
        导出aoi中心点为geojson

        Args:
        - id (int): aoi id
        - properties (Dict[str, Any] | str, optional): geojson的properties, 设置为"auto"时按照【如何与可视化团队交互】需要自动设置properties. Defaults to {}.

        Returns:
        - dict: geojson格式的dict
        """
        aoi = self.get_aoi(id)
        assert aoi is not None, f"aoi {id} not found"
        geometry = aoi["shapely_lnglat"].centroid
        if properties == "auto":
            properties = {
                "point_type": "aoi",
                "id": str(id),
                "aoi_type": str(aoi.get("land_use", 0)),
                "poi_ids": [str(pid) for pid in aoi["poi_ids"]],
            }
        feature = Feature(id=id, geometry=geometry, properties=properties)
        return dict(feature)

    def export_poi_as_geojson(
        self, id: int, properties: Union[Dict[str, Any], str] = "auto"
    ) -> dict:
        """
        导出poi为geojson

        Args:
        - id (int): poi id
        - properties (Dict[str, Any] | str, optional): geojson的properties, 设置为"auto"时按照【如何与可视化团队交互】需要自动设置properties. Defaults to "auto".

        Returns:
        - dict: geojson格式的dict
        """
        poi = self.get_poi(id)
        assert poi is not None, f"poi {id} not found"
        geometry = poi["shapely_lnglat"]
        if properties == "auto":
            properties = {
                "point_type": "poi",
                "id": str(id),
                "poi_type": poi["category"],
                "name": poi["name"],
                "address": "",
            }
        feature = Feature(id=id, geometry=geometry, properties=properties)
        return dict(feature)

    def export_lane_as_geojson(self, id: int, properties: Dict[str, Any] = {}) -> dict:
        """
        导出lane为geojson

        Args:
        - id (int): lane id
        - properties (Dict[str, Any], optional): geojson的properties. Defaults to {}.

        Returns:
        - dict: geojson格式的dict
        """
        lane = self.get_lane(id)
        assert lane is not None, f"lane {id} not found"
        geometry = lane["shapely_lnglat"]
        feature = Feature(id=id, geometry=geometry, properties=properties)
        return dict(feature)

    def export_road_as_geojson(self, id: int, properties: Dict[str, Any] = {}) -> dict:
        """
        导出road为geojson

        Args:
        - id (int): road id
        - properties (Dict[str, Any], optional): geojson的properties. Defaults to {}.

        Returns:
        - dict: geojson格式的dict
        """
        road = self.get_road(id)
        assert road is not None, f"road {id} not found"
        geometry = road["shapely_lnglat"]
        feature = Feature(id=id, geometry=geometry, properties=properties)
        return dict(feature)

    def _route_to_xys(
        self,
        route_req: routing_service.GetRouteRequest,
        route_res: routing_service.GetRouteResponse,
    ) -> np.ndarray:
        assert route_req.type in (
            routing_pb2.ROUTE_TYPE_DRIVING,
            routing_pb2.ROUTE_TYPE_WALKING,
        ), f"route type {route_req.type} not supported"
        is_walk = route_req.type == routing_pb2.ROUTE_TYPE_WALKING
        coordinates = []
        for journey in route_res.journeys:
            if is_walk:
                assert journey.type == routing_pb2.JOURNEY_TYPE_WALKING
            else:
                assert journey.type == routing_pb2.JOURNEY_TYPE_DRIVING
            # 处理起点处的截断
            lane_id, geo = (
                self._get_walking_geo(journey.walking.route[0])
                if is_walk
                else self._get_driving_geo(journey.driving.road_ids[0])
            )
            start_s = self._get_lane_s(route_req.start, lane_id)
            if len(journey.walking.route) == 1:
                end_s = self._get_lane_s(route_req.end, lane_id)
                geo = substring(geo, start_s, end_s)
            else:
                geo = substring(geo, start_s, geo.length)
            coordinates += list(geo.coords)
            # 处理中间的路段
            if is_walk:
                for route in journey.walking.route[1:-1]:
                    _, geo = self._get_walking_geo(route)
                    coordinates += list(geo.coords)
            else:
                for road_id in journey.driving.road_ids[1:-1]:
                    _, geo = self._get_driving_geo(road_id)
                    coordinates += list(geo.coords)
            if len(journey.walking.route) > 1:
                # 处理终点处的截断
                lane_id, geo = (
                    self._get_walking_geo(journey.walking.route[-1])
                    if is_walk
                    else self._get_driving_geo(journey.driving.road_ids[-1])
                )
                end_s = self._get_lane_s(route_req.end, lane_id)
                geo = substring(geo, 0, end_s)
                coordinates += list(geo.coords)
        if route_req.start.HasField("aoi_position"):
            aoi_center = self.aois[route_req.start.aoi_position.aoi_id][
                "shapely_xy"
            ].centroid.coords[0]
            coordinates = [aoi_center] + coordinates
        if route_req.end.HasField("aoi_position"):
            aoi_center = self.aois[route_req.end.aoi_position.aoi_id][
                "shapely_xy"
            ].centroid.coords[0]
            coordinates = coordinates + [aoi_center]
        coordinates = np.array(coordinates)
        return coordinates

    def export_route_as_geojson(
        self,
        route_req: Union[routing_service.GetRouteRequest, dict],
        route_res: Union[routing_service.GetRouteResponse, dict],
        properties: dict = {},
    ) -> dict:
        """
        导出route为geojson

        Args:
        - route_req (routing_service.GetRouteRequest): 请求导航的输入参数
        - route_res (routing_service.GetRouteResponse): 请求导航的输出结果
        - properties (dict, optional): geojson的properties. Defaults to {}.

        Returns:
        - dict: geojson格式的dict
        """
        if type(route_req) != routing_service.GetRouteRequest:
            route_req = ParseDict(route_req, routing_service.GetRouteRequest())
        if type(route_res) != routing_service.GetRouteResponse:
            route_res = ParseDict(route_res, routing_service.GetRouteResponse())

        coordinates = self._route_to_xys(route_req, route_res)
        # xy -> lnglat
        lngs, lats = self.projector(coordinates[:, 0], coordinates[:, 1], inverse=True)
        geo = LineString(list(zip(lngs, lats)))
        feature = Feature(geometry=geo, properties=properties)
        return dict(feature)

    def estimate_route_time(
        self,
        route_req: Union[routing_service.GetRouteRequest, dict],
        route_res: Union[routing_service.GetRouteResponse, dict],
    ) -> float:
        """
        估算导航路线的时间

        Args:
        - route_req (routing_service.GetRouteRequest): 请求导航的输入参数
        - route_res (routing_service.GetRouteResponse): 请求导航的输出结果
        - walking_speed (float, optional): 步行速度（单位：m/s）. Defaults to 1.1.

        Returns:
        - float: 估算的时间（单位：s）
        """
        if type(route_req) != routing_service.GetRouteRequest:
            route_req = ParseDict(route_req, routing_service.GetRouteRequest())
        if type(route_res) != routing_service.GetRouteResponse:
            route_res = ParseDict(route_res, routing_service.GetRouteResponse())

        is_walk = route_req.type == routing_pb2.ROUTE_TYPE_WALKING
        if is_walk:
            return sum(j.walking.eta for j in route_res.journeys)
        else:
            return sum(j.driving.eta for j in route_res.journeys)

    def query_pois(
        self,
        center: Tuple[float, float],
        radius: float,
        category_prefix: str,
        limit: Optional[int] = None,
    ) -> List[Tuple[Any, float]]:
        """
        查询center点指定半径内类别满足前缀的poi（按距离排序）

        Args:
        - center (x, y): 中心点（xy坐标系）
        - radius (float): 半径（单位：m）
        - category_prefix (str): 类别前缀，如实际类别为100000，那么匹配的前缀可以为10、1000等
        - limit (int, optional): 最多返回的poi数量，按距离排序，近的优先（默认None）.

        Returns
        - List[Tuple[Any, float]]: poi列表，每个元素为（poi, 距离）
        """

        point = Point(center)
        # 获取半径内的poi
        indices = self._poi_tree.query(point.buffer(radius))
        # 过滤掉不满足类别前缀的poi
        pois = []
        for index in indices:
            poi = self._poi_list[index]
            if poi["category"].startswith(category_prefix):
                distance = point.distance(poi["shapely_xy"])
                pois.append((poi, distance))
        # 按照距离排序
        pois = sorted(pois, key=lambda x: x[1])
        if limit is not None:
            pois = pois[:limit]
        return pois
