from pycitysim.map import Map

m = Map(
    mongo_uri="mongodb://username:password@url:port/",
    mongo_db="opencity",
    mongo_coll="map_beijing",
    cache_dir="./cache",
)

# 经纬度和地图平面坐标系转换
# Latitude and longitude and map plane coordinate system conversion
center = m.lnglat2xy(116.322, 39.983)
print(center)

# 查询圆半径内POI
pois = m.query_pois(center, 1000, "10", 10)
pois = m.query_pois(center, 1000, "10", 10)
print(pois)

# 查询圆半径内AOI
aois = m.query_aois(center, 1000, ["E3"], 10)
print(aois)

# 查询圆半径内Lane，返回[(lane, s, distance), ...]
# Query lanes within the radius of the circle, return [(lane, s, distance), ...]
lanes = m.query_lane(center, 100, 1)
print(lanes)

# 列出所有AOI ID
# List all AOI IDs
print(list(m.aois.keys())[:10])

# 查询AOI
# Query AOI
aoi = m.get_aoi(5_0000_0000)
print(aoi)

# 查询POI
# Query POI
poi = m.get_poi(7_0000_0000)
print(poi)
# 得到POI所在的AOI
# Get the AOI where the POI is located
print(poi["aoi_id"])

# 查询Lane
# Query Lane
lane = m.get_lane(0)
print(lane)
# 查询Road
# Query Road
road = m.get_road(2_0000_0000)
print(road)
# 查询Junction
# Query Junction
junction = m.get_junction(3_0000_0000)
print(junction)

# 导出AOI为GeoJSON（中心点）
# Export AOI as GeoJSON (center point)
feature = m.export_aoi_center_as_geojson(500033047)
print(feature)

# 导出POI为GeoJSON
# Export POI as GeoJSON
feature = m.export_poi_as_geojson(7_0000_0000)
print(feature)

# 导出Lane为GeoJSON
# Export Lane as GeoJSON
feature = m.export_lane_as_geojson(100)
print(feature)

# 导出Road为GeoJSON
# Export Road as GeoJSON
feature = m.export_road_as_geojson(2_0000_0000, {"name": "123", "xxx": "yyy"})
print(feature)
