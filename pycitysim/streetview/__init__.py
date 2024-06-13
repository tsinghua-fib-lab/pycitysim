"""
街景图片操作库
Street View Image Library
"""

from typing import List, Tuple
import requests

from .equirectangular import Equirectangular
from .baidu import BaiduStreetView
from .google import GoogleStreetView

__all__ = ["BaiduStreetView", "GoogleStreetView", "Equirectangular", "wgs842bd09mc"]


def wgs842bd09mc(
    coords: List[Tuple[float, float]], ak: str
) -> List[Tuple[float, float]]:
    """
    坐标转换：WGS84 -> BD09MC
    Coordinate transformation: WGS84 -> BD09MC

    Args:
    - coords: 需转换的源坐标，多组坐标以“;”分隔（经度,纬度）。The source coordinates to be converted, separated by ";" (longitude, latitude).
    - ak: 百度地图开发者密钥。Baidu Map Developer Key.

    Returns:
    - points: 转换后的坐标。The converted coordinates.
    """
    if len(coords) > 100:
        raise ValueError("coords too many")
    coordstr = ";".join([f"{x[0]},{x[1]}" for x in coords])
    url = f"http://api.map.baidu.com/geoconv/v1/?coords={coordstr}&from=1&to=6&ak={ak}"
    resp = requests.get(url)
    result = resp.json()
    xys = [(one["x"], one["y"]) for one in result["result"]]
    return xys
