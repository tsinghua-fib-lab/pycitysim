from pycitysim.streetview import (
    BaiduStreetView,
    GoogleStreetView,
    Equirectangular,
    wgs842bd09mc,
)

# 自行申请，具有“坐标转换”功能
# Apply for it yourself, with the function of "coordinate transformation"
AK = "百度地图AK"

# 1. WGS84 -> BD09MC 坐标转换
# 1. WGS84 -> BD09MC Coordinate Transformation
coords = [(116.404, 39.915)]
points = wgs842bd09mc(coords, AK)

# 2. 搜索街景
# 2. Search for street view
sv = BaiduStreetView.search(points[0][0], points[0][1], cache_dir="cache/")
sv.panorama.save("cache/panorama.jpg")

# 3. 全景图 -> 普通透视图
# 3. Panorama -> Normal Perspective View
eq = Equirectangular(sv)
persp = eq.get_perspective(90, 0, 20, 512, 1024)
persp.save("cache/persp.jpg")

# Google街景。Google Street View.
sv = GoogleStreetView.search(
    -74.0881915,
    40.7211232,
    2,
    proxies={"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
    cache_dir="cache/",
)

sv.panorama.save("cache/google-panorama.jpg")

# 全景图 -> 普通透视图
# Panorama -> Normal Perspective View
eq = Equirectangular(sv)
persp = eq.get_perspective(90, 0, 20, 512, 1024)
persp.save("cache/google-persp.jpg")
