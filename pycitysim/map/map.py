import gc
import os
import pickle
import warnings
from copy import deepcopy
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
import pyproj
import shapely
import stringcase
from geojson import Feature
from google.protobuf.json_format import ParseDict, MessageToDict
from pycityproto.city.geo.v2 import geo_pb2
from pycityproto.city.map.v2 import map_pb2
from pycityproto.city.routing.v2 import routing_pb2
from pycityproto.city.routing.v2 import routing_service_pb2 as routing_service
from pymongo import MongoClient
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring, unary_union

__all__ = ["Map"]


class Map:
    """
    模拟器地图API
    Simulator Map API
    """

    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        mongo_db: Optional[str] = None,
        mongo_coll: Optional[str] = None,
        cache_dir: Optional[str] = None,
        pb_path: Optional[str] = None,
    ):
        """
        Args:
        - mongo_uri (Optional[str]): mongo数据库的uri。MongoDB uri.
        - mongo_db (Optional[str]): 数据库名。Database name.
        - mongo_coll (Optional[str]): 集合名。Collection name.
        - cache_dir (Optional[str]): 缓存目录, Defaults to None. Cache directory, Defaults to None.
        - pb_path (Optional[str]): pb文件路径, Defaults to None. pb file path, Defaults to None.

        Users can init Map with either mongo_uri, mongo_db, mongo_coll or pb_path.
        """
        if cache_dir is None:
            # 显示runtime warning
            warnings.warn(
                "You are not using cache. "
                "It is recommended to use cache when you are using map data."
            )
        map_data = None
        if mongo_uri is not None and mongo_db is not None and mongo_coll is not None:
            map_data = self._download_map_with_cache(
                mongo_uri, mongo_db, mongo_coll, cache_dir
            )
        if pb_path is not None:
            with open(pb_path, "rb") as f:
                pb = map_pb2.Map().FromString(f.read())
            jsons = []
            for field in pb.DESCRIPTOR.fields:
                class_name = stringcase.spinalcase(field.message_type.name)
                if field.label == field.LABEL_REPEATED:
                    for pb_field in getattr(pb, field.name):
                        data = MessageToDict(
                            pb_field,
                            including_default_value_fields=True,
                            preserving_proto_field_name=True,
                            use_integers_for_enums=True,
                        )
                        jsons.append({"class": class_name, "data": data})
                else:
                    data = MessageToDict(
                        getattr(pb, field.name),
                        including_default_value_fields=True,
                        preserving_proto_field_name=True,
                        use_integers_for_enums=True,
                    )
                    jsons.append({"class": class_name, "data": data})
            map_data = self._parse_map(jsons)
        if map_data is None:
            raise ValueError(
                "You must provide either (mongo_uri, mongo_db, mongo_coll) or pb_path"
            )

        self.header: dict = map_data["header"]
        """
        地图元数据，包含如下属性:
        Map metadata, including the following attributes:
        - name (string): 城市道路名称，供标识数据集合的语义。Map name, to identify the semantics of data collections.
        - date (string): 城市道路数据的创建时间。Map data creation time.
        - north (float): 道路数据的北边界坐标。The coordinate of the northern boundary of the Map data.
        - south (float): 道路数据的南边界坐标。The coordinate of the southern boundary of the Map data.
        - east (float): 道路数据的东边界坐标。The coordinate of the eastern boundary of the Map data.
        - west (float): 道路数据的西边界坐标。The coordinate of the western boundary of the Map data.
        - projection (string): PROJ.4 投影字符串，用以支持xy坐标到其他坐标系的转换。PROJ.4 projection string to support the conversion of xy coordinates to other coordinate systems.
        """

        self.juncs: Dict[int, dict] = map_data["juncs"]
        """
        地图中的路口集合（junction），字典的值包含如下属性:
        The intersection collection (junction) in the map, the value of the dictionary contains the following attributes:
        - id (int): 路口编号。Junction ID.
        - lane_ids (list[int]): 属于该路口的所有车道和人行道编号。IDs of all driving and pedestrian lanes belonging to this junction.
        - center (Dict[str, float]): 路口的大致中心点。The approximate center of the junction. example: {'x': 5983.14, 'y': 1807.73}
        """

        self.lanes: Dict[int, dict] = map_data["lanes"]
        """
        地图中的车道集合（lane），字典的值包含如下属性:
        The lane collection (lane) in the map. The value of the dictionary contains the following attributes:
        - id (int): 车道编号。Lane ID.
        - type (int): 车道类型 (1:行车|2:步行)。Lane type (1: Driving | 2: Pedestrian).
        - turn (int): 转向类型 (1:直行|2:左转|3: 右转|4: 掉头)。Turn type (1: straight | 2: left | 3: right | 4: around).
        - max_speed (float): 最大速度限制(单位: m/s)。Maximum speed limit (m/s).
        - length (float): 车道中心线的长度(单位: m)。Length of lane centerline (m).
        - width (float): 车道的宽度(单位: m)。Lane width.
        - center_line (list[XYPosition]): 车道中心线的形状。Lane centerline shape.
        - predecessors (list[LaneConnection]): 前驱车道编号和连接类型。对于路口内的车道，最多只有一个前驱车道。对于 LANE_TYPE_DRIVING，连接类型必须是 LANE_CONNECTION_TYPE_TAIL。对于 LANE_TYPE_WALKING，两种连接类型都可能。ID and connection type of predecessor lanes. For lanes within a junction, there is at most one predecessor lane. For LANE_TYPE_DRIVING, the connection type must be LANE_CONNECTION_TYPE_TAIL. For LANE_TYPE_WALKING, both connection types are possible.
        - successors (list[LaneConnection]): 后继车道编号和连接类型。对于路口内的车道，最多只有一个后继车道。对于 LANE_TYPE_DRIVING，连接类型必须是 LANE_CONNECTION_TYPE_HEAD。对于 LANE_TYPE_WALKING，两种连接类型都可能。ID and connection type of successor lanes. For lanes within a junction, there is at most one successor lane. For LANE_TYPE_DRIVING, the connection type must be LANE_CONNECTION_TYPE_HEAD. For LANE_TYPE_WALKING, both connection types are possible.
        - left_lane_ids (list[int]): 左侧相邻车道的车道编号，从最近到最远排列。Lane IDs of the adjacent lanes on the left, arranged from closest to furthest.
        - right_lane_ids (list[int]): 右侧相邻车道的车道编号，从最近到最远排列。Lane IDs of the adjacent lanes on the right, arranged from closest to furthest.
        - parent_id (int): 车道所属的道路/路口编号。The road/intersection ID to which the lane belongs.
        - aoi_ids (list[int]): 与车道连接的 AOI 编号。AOI IDs connected to the lane.
        - shapely_xy (shapely.geometry.LineString): 车道中心线的形状（xy坐标系）。Shape of lane centerline (in xy coordinates).
        - shapely_lnglat (shapely.geometry.LineString): 车道中心线的形状（经纬度坐标系）Shape of lane centerline (in latitude and longitude).
        """

        self.roads: Dict[int, dict] = map_data["roads"]
        """
        地图中的道路集合（road），字典的值包含如下属性:
        The road collection (road) in the map, the value of the dictionary contains the following attributes:
        - id (int): 道路编号。Road ID.
        - lane_ids (list[int]): 道路所包含的车道和人行道编号。Driving and pedestrian lane IDs that the road contains.
        """

        self.aois: Dict[int, dict] = map_data["aois"]
        """
        地图中的AOI集合（aoi），字典的值包含如下属性:
        AOI collection (aoi) in the map, the value of the dictionary contains the following attributes:
        - id (int): AOI编号。AOI ID.
        - positions (list[XYPosition]): 多边形空间范围。Shape of polygon.
        - area (float): 面积(单位: m2)。Area.
        - driving_positions (list[LanePosition]): 和道路网中行车道的连接点。Connection points to driving lanes.
        - walking_positions (list[LanePosition]): 和道路网中人行道的连接点。Connection points to pedestrian lanes.
        - driving_gates (list[XYPosition]): 和道路网中行车道的连接点对应的AOI边界上的位置。Position on the AOI boundary corresponding to the connection point to driving lanes.
        - walking_gates (list[XYPosition]): 和道路网中人行道的连接点对应的AOI边界上的位置。Position on the AOI boundary corresponding to the connection point to pedestrian lanes.
        - urban_land_use (Optional[str]): 城市建设用地分类，参照执行标准GB 50137-2011（https://www.planning.org.cn/law/uploads/2013/1383993139.pdf） Urban Land use type, refer to the national standard GB 50137-2011.
        - poi_ids (list[int]): 包含的POI列表。Contained POI IDs.
        - shapely_xy (shapely.geometry.Polygon): AOI的形状（xy坐标系）。Shape of polygon (in xy coordinates).
        - shapely_lnglat (shapely.geometry.Polygon): AOI的形状（经纬度坐标系）。Shape of polygon (in latitude and longitude).
        """

        self.pois: Dict[int, dict] = map_data["pois"]
        """
        地图中的POI集合（poi），字典的值包含如下属性:
        POI collection (poi) in the map, the value of the dictionary contains the following attributes:
        - id (int): POI编号。POI ID.
        - name (string): POI名称。POI name.
        - category (string): POI类别编码。POI category code.
        - position (XYPosition): POI位置。POI position.
        - aoi_id (int): POI所属的AOI编号。AOI ID to which the POI belongs.
        """

        self.projector: pyproj.Proj = map_data["projector"]
        """
        采用PROJ.4投影字符串创建的转换器，用以支持xy坐标到WGS84坐标系的转换
        Converter created using PROJ.4 projection string to support conversion of xy coordinates to WGS84 coordinate system
        """
        (
            self._aoi_tree,
            self._aoi_list,
            self._poi_tree,
            self._poi_list,
            self._driving_lane_tree,
            self._driving_lane_list,
            self._walking_lane_tree,
            self._walking_lane_list,
        ) = self._build_geo_index()

    def _parse_map(self, m: List[Any]) -> Dict[str, Any]:
        # client = MongoClient(uri)
        # m = list(client[db][coll].find({}))
        header = None
        juncs = {}
        roads = {}
        lanes = {}
        aois = {}
        pois = {}
        for d in m:
            if "_id" in d:
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
        # 为junction解算大致的中心点
        for junc in juncs.values():
            lane_shapelys = [
                lanes[lane_id]["shapely_xy"] for lane_id in junc["lane_ids"]
            ]
            geos = unary_union(lane_shapelys)
            center = geos.centroid
            junc["center"] = {"x": center.x, "y": center.y}

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
        def _download_map(uri: str, db: str, coll: str):
            client = MongoClient(uri)
            m = list(client[db][coll].find({}))
            return self._parse_map(m)

        if cache_dir is None:
            return _download_map(uri, db, coll)
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
            m = _download_map(uri, db, coll)
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
        # }
        aoi_list = list(self.aois.values())
        aoi_tree = shapely.STRtree([aoi["shapely_xy"] for aoi in aoi_list])
        poi_list = list(self.pois.values())
        poi_tree = shapely.STRtree([poi["shapely_xy"] for poi in poi_list])
        driving_lane_list = [
            lane for lane in self.lanes.values() if lane["type"] == 1  # driving
        ]
        driving_lane_tree = shapely.STRtree(
            [lane["shapely_xy"] for lane in driving_lane_list]
        )
        walking_lane_list = [
            lane for lane in self.lanes.values() if lane["type"] == 2  # walking
        ]
        walking_lane_tree = shapely.STRtree(
            [lane["shapely_xy"] for lane in walking_lane_list]
        )
        return (
            aoi_tree,
            aoi_list,
            poi_tree,
            poi_list,
            driving_lane_tree,
            driving_lane_list,
            walking_lane_tree,
            walking_lane_list,
        )

    def _get_lane_s(self, position: geo_pb2.Position, lane_id: int) -> float:
        """
        解算position对应的在lane_id上的s值
        Solve the s value corresponding to position on lane_id
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
        Obtain the Lane ID and Lane's geometric information corresponding to the geometric information based on the road ID.
        """
        road = self.roads[road_id]
        aoi_lane_id = road["driving_lane_ids"][-1]
        geo: LineString = road["shapely_xy"]
        return aoi_lane_id, geo

    def _get_walking_geo(self, segment: routing_pb2.WalkingRouteSegment):
        """
        根据步行路段（导航结果）获取几何信息对应的Lane ID和Lane的几何信息
        Obtain the Lane ID and Lane's geometric information corresponding to the geometric information based on the walking path (navigation result).
        """
        lane_id = segment.lane_id
        direction = segment.moving_direction
        geo: LineString = self.lanes[lane_id]["shapely_xy"]
        if direction == routing_pb2.MOVING_DIRECTION_BACKWARD:
            geo: LineString = geo.reverse()
        return lane_id, geo

    def lnglat2xy(self, lng: float, lat: float) -> Tuple[float, float]:
        """
        经纬度转xy坐标
        Convert latitude and longitude to xy coordinates

        Args:
        - lng (float): 经度。longitude.
        - lat (float): 纬度。latitude.

        Returns:
        - Tuple[float, float]: xy坐标。xy coordinates.
        """
        return self.projector(lng, lat)

    def xy2lnglat(self, x: float, y: float) -> Tuple[float, float]:
        """
        xy坐标转经纬度
        xy coordinates to longitude and latitude

        Args:
        - x (float): x坐标。x coordinate.
        - y (float): y坐标。y coordinate.

        Returns:
        - Tuple[float, float]: 经纬度。Longitude and latitude.

        """
        return self.projector(x, y, inverse=True)

    def get_header(self):
        """
        查询header
        query header
        """
        return self.header

    def get_aoi(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询AOI
        query AOI

        Args:
        - id (int): AOI id
        - include_unused (bool, optional): 是否包含未使用或无效的AOI属性. Defaults to False. Whether contains unused or invalid AOI attributes. Defaults to False.

        Returns:
        - Optional[Any]: AOI（经过复制后的dict）。AOI (copied dict).
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
        query poi

        Args:
        - id (int): poi id
        - include_unused (bool, optional): 是否包含未使用或无效的poi属性. Defaults to False. Whether contains unused or invalid POI attributes. Defaults to False.

        Returns:
        - Optional[Any]: poi（经过复制后的dict）。POI (copied dict).
        """
        doc = self.pois.get(id)
        if doc is None:
            return None
        doc = deepcopy(doc)
        if not include_unused:
            ...
        return doc

    def get_lane(self, id: int, include_unused: bool = False) -> Optional[Any]:
        """
        查询lane
        query lane

        Args:
        - id (int): lane id
        - include_unused (bool, optional): 是否包含未使用或无效的lane属性. Defaults to False. Whether contains unused or invalid lane attributes. Defaults to False.

        Returns:
        - Optional[Any]: lane（经过复制后的dict）。Lane (copied dict).
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
        query road

        Args:
        - id (int): road id
        - include_unused (bool, optional): 是否包含未使用或无效的road属性. Defaults to False. Whether contains unused or invalid road attributes. Defaults to False.

        Returns:
        - Optional[Any]: road（经过复制后的dict）。Road (copied dict).
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
        query junction

        Args:
        - id (int): junction id
        - include_unused (bool, optional): 是否包含未使用或无效的junction属性. Defaults to False.  Whether contains unused or invalid junction attributes. Defaults to False.

        Returns:
        - Optional[Any]: junction（经过复制后的dict）。Junction (copied dict).
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
        properties: Union[Dict[str, Any], Literal["auto"]] = "auto",
    ) -> dict:
        """
        导出aoi中心点为geojson
        Export aoi center point as geojson

        Args:
        - id (int): aoi id
        - properties (Dict[str, Any] | str, optional): geojson的properties, 设置为"auto"时包含aoi类别与所含的poi列表. Defaults to {}. Geojson's properties, when set to "auto", the properties include aoi category and the list of contained poi. Defaults to {}.

        Returns:
        - dict: geojson格式的dict。dict in geojson format.
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

    def export_aoi_as_geojson(
        self, id: int, properties: Union[Dict[str, Any], Literal["auto"]] = "auto"
    ) -> dict:
        """
        导出aoi为geojson
        Export aoi as geojson

        Args:
        - id (int): aoi id
        - properties (Dict[str, Any] | str, optional): geojson的properties, 设置为"auto"时包含aoi类别与所含的poi列表. Defaults to {}. Geojson's properties, when set to "auto", the properties include aoi category and the list of contained poi. Defaults to {}.

        Returns:
        - dict: geojson格式的dict。dict in geojson format.
        """
        aoi = self.get_aoi(id)
        assert aoi is not None, f"aoi {id} not found"
        geometry = aoi["shapely_lnglat"]
        if properties == "auto":
            properties = {
                "aoi_type": str(aoi.get("land_use", 0)),
                "poi_ids": [str(pid) for pid in aoi.get("poi_ids", [])],
            }
        feature = Feature(id=id, geometry=geometry, properties=properties)
        return dict(feature)

    def export_poi_as_geojson(
        self, id: int, properties: Union[Dict[str, Any], Literal["auto"]] = "auto"
    ) -> dict:
        """
        导出poi为geojson
        Export poi as geojson

        Args:
        - id (int): poi id
        - properties (Dict[str, Any] | str, optional): geojson的properties, 设置为"auto"时包含poi类别、名称. Defaults to "auto". Geojson's properties, when set to "auto", the properties include poi category and name. Defaults to "auto".

        Returns:
        - dict: geojson格式的dict. dict in geojson format.
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

    def export_lane_as_geojson(
        self, id: int, properties: Union[Dict[str, Any], Literal["auto"]] = "auto"
    ) -> dict:
        """
        导出lane为geojson
        geojson的properties. Defaults to {}.

        Args:
        - id (int): lane id
        - properties (Dict[str, Any], optional): geojson的properties. Defaults to "auto"（含lane的类别、转向类别、父对象ID、最大车速）. geojson properties. Defaults to {}. (including lane type, turn type, parent object ID, maximum vehicle speed).

        Returns:
        - dict: geojson格式的dict。dict in geojson format.
        """
        lane = self.get_lane(id)
        assert lane is not None, f"lane {id} not found"
        geometry = lane["shapely_lnglat"]
        if properties == "auto":
            properties = {
                "id": str(id),
                "lane_type": str(lane["type"]),
                "lane_turn": str(lane["turn"]),
                "parent_id": str(lane["parent_id"]),
                "max_speed": lane["max_speed"],
            }
        feature = Feature(id=id, geometry=geometry, properties=properties)
        return dict(feature)

    def export_road_as_geojson(self, id: int, properties: Dict[str, Any] = {}) -> dict:
        """
        导出road为geojson
        Export road as geojson

        Args:
        - id (int): road id
        - properties (Dict[str, Any], optional): geojson的properties. Defaults to {}. geojson properties. Defaults to {}.

        Returns:
        - dict: geojson格式的dict。dict in geojson format.
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
        Export route as geojson

        Args:
        - route_req (routing_service.GetRouteRequest): 请求导航的输入参数。Input parameters for request navigation.
        - route_res (routing_service.GetRouteResponse): 请求导航的输出结果。Output results for request navigation.
        - properties (dict, optional): geojson的properties. Defaults to {}. geojson properties. Defaults to {}.

        Returns:
        - dict: geojson格式的dict。dict in geojson format.
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
        Estimate navigation route time

        Args:
        - route_req (routing_service.GetRouteRequest): 请求导航的输入参数。Input parameters for request navigation.
        - route_res (routing_service.GetRouteResponse): 请求导航的输出结果。Output results for request navigation.
        - walking_speed (float, optional): 步行速度（单位：m/s）. Defaults to 1.1. Walking speed (unit: m/s). Defaults to 1.1.

        Returns:
        - float: 估算的时间（单位：s）。Estimated time (unit: s).
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
        center: Union[Tuple[float, float], Point],
        radius: float,
        category_prefix: str,
        limit: Optional[int] = None,
    ) -> List[Tuple[Any, float]]:
        """
        查询center点指定半径内类别满足前缀的poi（按距离排序）。Query the POIs whose categories satisfy the prefix within the specified radius of the center point (sorted by distance).

        Args:
        - center (x, y): 中心点（xy坐标系）。Center point (xy coordinate system).
        - radius (float): 半径（单位：m）。Radius (unit: m).
        - category_prefix (str): 类别前缀，如实际类别为100000，那么匹配的前缀可以为10、1000等。Category prefix, if the actual category is 100000, then the matching prefix can be 10, 1000, etc.
        - limit (int, optional): 最多返回的poi数量，按距离排序，近的优先（默认None）. The maximum number of POIs returned, sorted by distance, closest ones first (default to None).

        Returns:
        - List[Tuple[Any, float]]: poi列表，每个元素为（poi, 距离）。poi list, each element is (poi, distance).
        """
        if not isinstance(center, Point):
            center = Point(center)
        # 获取半径内的poi
        indices = self._poi_tree.query(center.buffer(radius))
        # 过滤掉不满足类别前缀的poi
        pois = []
        for index in indices:
            poi = self._poi_list[index]
            if poi["category"].startswith(category_prefix):
                distance = center.distance(poi["shapely_xy"])
                pois.append((poi, distance))
        # 按照距离排序
        pois = sorted(pois, key=lambda x: x[1])
        if limit is not None:
            pois = pois[:limit]
        return pois

    def query_aois(
        self,
        center: Union[Tuple[float, float], Point],
        radius: float,
        urban_land_uses: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[Any, float]]:
        """
        查询center点指定半径内城市用地满足条件的aoi（按距离排序）。Query the AOIs whose urban land use within the specified radius of the center point meets the conditions (sorted by distance).

        Args:
        - center (x, y): 中心点（xy坐标系）。Center point (xy coordinate system).
        - radius (float): 半径（单位：m）。Radius (unit: m).
        - urban_land_uses (List[str], optional): 城市用地分类列表，参照执行标准GB 50137-2011（https://www.planning.org.cn/law/uploads/2013/1383993139.pdf）. Urban land use classification list, refer to the national standard GB 50137-2011.
        - limit (int, optional): 最多返回的aoi数量，按距离排序，近的优先（默认None）. The maximum number of AOIs returned, sorted by distance, closest ones first (default to None).

        Returns:
        - List[Tuple[Any, float]]: aoi列表，每个元素为（aoi, 距离）。aoi list, each element is (aoi, distance).
        """

        if not isinstance(center, Point):
            center = Point(center)
        # 获取半径内的aoi
        indices = self._aoi_tree.query(center.buffer(radius))
        # 过滤掉不满足城市用地条件的aoi
        aois = []
        for index in indices:
            aoi = self._aoi_list[index]
            if (
                urban_land_uses is not None
                and aoi["urban_land_use"] not in urban_land_uses
            ):
                continue
            distance = center.distance(aoi["shapely_xy"])
            aois.append((aoi, distance))
        # 按照距离排序
        aois = sorted(aois, key=lambda x: x[1])
        if limit is not None:
            aois = aois[:limit]
        return aois

    def query_lane(
        self,
        xy: Union[Tuple[float, float], Point],
        radius: float,
        lane_type: int = 1,
    ):
        """
        查询xy点指定半径内的lane和s坐标
        Query the lane and s coordinates within the specified radius of the xy point.

        Args:
        - xy (x, y): 中心点（xy坐标系）。Center point (xy coordinate system).
        - radius (float): 半径（单位：m），超出半径则返回空列表。Radius (unit: m), if the radius is exceeded, an empty list will be returned.
        - lane_type (int): 车道类型（1:行车，默认|2:步行）。Lane type (1: driving, default | 2: walking).

        Returns:
        - List[Tuple[Any, float, float]]: lane列表，每个元素为（lane, s, 距离）。lane list, each element is (lane, s, distance).
        """

        if not isinstance(xy, Point):
            xy = Point(xy)
        if lane_type == 1:
            indices = self._driving_lane_tree.query(xy.buffer(radius))
            lanes = [self._driving_lane_list[index] for index in indices]
        elif lane_type == 2:
            indices = self._walking_lane_tree.query(xy.buffer(radius))
            lanes = [self._walking_lane_list[index] for index in indices]
        else:
            raise ValueError(f"lane_type {lane_type} not supported")
        result = []  # (lane, s, distance)
        # 计算距离和s坐标
        for lane in lanes:
            distance = xy.distance(lane["shapely_xy"])
            if distance > radius:
                continue
            s = lane["shapely_xy"].project(xy)
            result.append((lane, s, distance))
        # 按距离排序
        result = sorted(result, key=lambda x: x[2])

        return result
