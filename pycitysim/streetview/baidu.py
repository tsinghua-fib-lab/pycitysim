from pathlib import Path
import pickle
from io import BytesIO
from typing import Dict, Optional, Union

import requests
from PIL import Image

__all__ = ["BaiduStreetView"]


class BaiduStreetView:
    def __init__(
        self,
        sid: str,
        zoom: int = 4,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ):
        self.sid = sid
        self._zoom = zoom
        self._headers = headers
        self._proxies = proxies
        self.meta = self._query_camera()
        """
        设备信息，关键字段如下（用于调整取出照片时的方位）：
        Camera Information, the useful fields are as follows (used to adjust the orientation of the taken photo):
        - "Heading": 拍摄时的朝向（单位：度），全景相片的0度方向总是为拍摄时朝向的左侧，90度为正前方，180度为拍摄时朝向的右侧，270度为正后方。The direction of the photo taken (unit: degree), the 0-degree direction of the panorama photo is always to the left of the direction when the photo was taken, 90 degrees is the front, 180 degrees is to the right of the direction when the photo was taken, and 270 degrees is the back.
        - "Pitch": 拍摄时的俯仰角（单位：度），范围为[-90, 90]，0度为水平方向，90度为垂直向上，-90度为垂直向下。The pitch angle when the photo was taken (unit: degree), the range is [-90, 90], 0 degrees is the horizontal direction, 90 degrees is vertical up, and -90 degrees is vertical down.
        - "X"/"Y"/"Z": 拍摄时的坐标（单位：米），BD09MC坐标系。The coordinates when the photo was taken (unit: meter), BD09MC coordinate system.
        - "Rname": 拍摄时的道路名称。The road name when the photo was taken.
        """
        self.panorama = self._query_img()
        """
        全景图，采用Equirectangular转换为普通透视图后可用于显示。
        Panorama, which can be used for display after being converted to a normal perspective view using Equirectangular.
        """

    @property
    def heading(self) -> float:
        """
        获取拍摄时的朝向（单位：度）
        Get the direction when the photo was taken (unit: degree)
        """
        return self.meta["Heading"]

    @staticmethod
    def search(
        x,
        y,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
        cache_dir: Union[str, Path, None] = None,
    ) -> "BaiduStreetView":
        """
        街景图片信息查询
        Street view image information query

        Args:
        - x: x坐标（BD09MC）。x coordinate (BD09MC)
        - y: y坐标（BD09MC）。y coordinate (BD09MC)
        - cache_dir: 缓存目录，若为None则不缓存。Cache directory, if None, no cache.

        Returns:
        - sv: 街景图片。Street view image.
        """
        url = f"https://mapsv0.bdimg.com/?qt=qsdata&x={x}&y={y}"
        resp = requests.get(url)
        result = resp.json()
        # 正确响应格式：{'content': {'RoadId': 'c68cdd-64ba-7b9a-549d-82eac9', 'RoadName': '锡拉胡同', 'id': '09002200121707120825100452M', 'x': 1295957900, 'y': 482703000}, 'result': {'action': 0, 'error': 0}}
        # 失败响应格式：{'result': {'action': 0, 'error': 400}}
        if result["result"]["error"] != 0:
            raise ValueError(f"invalid qsdata response: {result}")
        sid = result["content"]["id"]

        # 检查缓存
        if cache_dir is not None:
            if isinstance(cache_dir, str):
                cache_dir = Path(cache_dir)
            # 检查缓存目录是否存在，不存在则创建
            if not cache_dir.exists():
                cache_dir.mkdir(parents=True)
            cache_file = cache_dir / f"{sid}.pkl"
        else:
            cache_file = None
        if cache_file is not None and cache_file.exists():
            with open(cache_file, "rb") as f:
                sv = pickle.load(f)
        else:
            sv = BaiduStreetView(sid, headers=headers, proxies=proxies)
            if cache_file is not None:
                with open(cache_file, "wb") as f:
                    pickle.dump(sv, f)
        return sv

    def _query_camera(self):
        url = f"https://mapsv0.bdimg.com/?qt=sdata&sid={self.sid}"
        resp = requests.get(url)
        result = resp.json()
        if result["result"]["error"] != 0 or len(result["content"]) != 1:
            raise ValueError(f"invalid sdata response: {result}")
        return result["content"][0]

    def _query_img(self):
        # 1. 下载全景图
        if self._zoom == 1:
            xrange, yrange = 1, 1
        elif self._zoom == 2:
            xrange, yrange = 1, 2
        elif self._zoom == 3:
            xrange, yrange = 2, 4
        elif self._zoom == 4:
            xrange, yrange = 4, 8
        else:
            raise ValueError(f"invalid zoom: {self._zoom}")
        imgs = []
        with requests.Session() as s:
            for x in range(xrange):
                for y in range(yrange):
                    url = f"https://mapsv0.bdimg.com/?qt=pdata&sid={self.sid}&pos={x}_{y}&z={self._zoom}&from=PC"
                    with s.get(url) as resp:
                        b = resp.content
                        img = Image.open(BytesIO(b))
                        imgs.append(img)

        # 2. 拼接全景图
        w, h = imgs[0].size
        width = w * yrange
        height = h * xrange
        panorama = Image.new("RGB", (width, height))
        for i, img in enumerate(imgs):
            x = i // yrange
            y = i % yrange
            panorama.paste(
                img,
                (
                    y * h,
                    x * w,
                ),
            )
        return panorama
