from pathlib import Path
import json
import re
from typing import List, Optional, Dict, Union
import itertools
import pickle
from io import BytesIO

import requests
from dataclasses import dataclass
from PIL import Image

__all__ = ["Panorama", "GoogleStreetView"]


@dataclass
class Panorama:
    pano_id: str
    lat: float
    lon: float
    heading: float
    pitch: Optional[float]
    roll: Optional[float]
    date: Optional[str]


class GoogleStreetView:

    def __init__(
        self,
        meta: Panorama,
        zoom: int = 4,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ):
        self.meta: Panorama = meta
        self._zoom = zoom
        self._headers = headers
        self._proxies = proxies
        self._raw_panorama, self.panorama = self._query_img()

    @property
    def heading(self) -> float:
        """
        获取拍摄时的朝向（单位：度）（统一到百度的heading计算方式上）
        Get the direction when the photo was taken (unit: degree) (unified to the heading calculation method of Baidu)
        """
        return self.meta.heading + 90

    @staticmethod
    def _extract_meta(text: str) -> List[Panorama]:
        """
        从panoids端点的有效响应中返回所有全景图的列表。
        Given a valid response from the panoids endpoint, return a list of all the
        panoids.
        """

        # The response is actually javascript code. It's a function with a single
        # input which is a huge deeply nested array of items.
        blob = re.findall(r"callbackfunc\( (.*) \)$", text)[0]
        data = json.loads(blob)

        if data == [[5, "generic", "Search returned no images."]]:
            return []

        subset = data[1][5][0]

        raw_panos = subset[3][0]

        if len(subset) < 9 or subset[8] is None:
            raw_dates = []
        else:
            raw_dates = subset[8]

        # For some reason, dates do not include a date for each panorama.
        # the n dates match the last n panos. Here we flip the arrays
        # so that the 0th pano aligns with the 0th date.
        raw_panos = raw_panos[::-1]
        raw_dates = raw_dates[::-1]

        dates = [f"{d[1][0]}-{d[1][1]:02d}" for d in raw_dates]

        return [
            Panorama(
                pano_id=pano[0][1],
                lat=pano[2][0][2],
                lon=pano[2][0][3],
                heading=pano[2][2][0],
                pitch=pano[2][2][1] if len(pano[2][2]) >= 2 else None,
                roll=pano[2][2][2] if len(pano[2][2]) >= 3 else None,
                date=dates[i] if i < len(dates) else None,
            )
            for i, pano in enumerate(raw_panos)
        ]

    @staticmethod
    def search(
        lng: float,
        lat: float,
        zoom: int = 4,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
        cache_dir: Union[str, Path, None] = None,
    ) -> "GoogleStreetView":
        """
        获取最接近GPS坐标的全景图（ids）。
        Gets the closest panoramas (ids) to the GPS coordinates.

        Args:
        - lng: 经度 (WGS84)。Longitude (WGS84).
        - lat: 纬度 (WGS84)。Latitude (WGS84).
        - zoom: 缩放级别，越大图像质量越高，最大为4（可选，默认为4）。Zoom level, the larger the image quality, the higher the maximum is 4 (optional, default is 4).
        - proxies: 代理（可选）。Proxies (optional).
        - cache_dir: 缓存目录，若为None则不缓存。Cache directory, if None, no cache.

        Returns:
        - sv: 街景图片。Street view image.
        """
        url = (
            "https://maps.googleapis.com/maps/api/js/"
            "GeoPhotoService.SingleImageSearch"
            f"?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d50!3m10"
            "!2m2!1sen!2sGB!9m1!1e2!11m4!1m3!1e2!2b1!3e2!4m10!1e1!1e2!1e3!1e4"
            "!1e8!1e6!5m1!1e2!6m1!1e2"
            "&callback=callbackfunc"
        )
        resp = requests.get(url, proxies=proxies)
        pans = GoogleStreetView._extract_meta(resp.text)
        if len(pans) == 0:
            raise ValueError("No panoramas found.")
        pan = pans[0]
        pid = pan.pano_id

        # 检查缓存
        if cache_dir is not None:
            if isinstance(cache_dir, str):
                cache_dir = Path(cache_dir)
            # 检查缓存目录是否存在，不存在则创建
            if not cache_dir.exists():
                cache_dir.mkdir(parents=True)
            cache_file = cache_dir / f"{pid}.pkl"
        else:
            cache_file = None
        if cache_file is not None and cache_file.exists():
            with open(cache_file, "rb") as f:
                sv = pickle.load(f)
        else:
            sv = GoogleStreetView(pan, zoom, headers=headers, proxies=proxies)
            if cache_file is not None:
                with open(cache_file, "wb") as f:
                    pickle.dump(sv, f)

        return sv

    def _query_img(self):
        """
        下载Google全景图
        Downloads a streetview panorama.
        """

        tile_width = 512
        tile_height = 512

        total_width, total_height = 2**self._zoom, 2 ** (self._zoom - 1)
        raw = Image.new("RGB", (total_width * tile_width, total_height * tile_height))

        with requests.Session() as s:
            for x, y in itertools.product(range(total_width), range(total_height)):
                url = f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile&panoid={self.meta.pano_id}&x={x}&y={y}&zoom={self._zoom}"  # 可以增加参数nbt=1（no black tile），但是会导致部分图片返回400错误
                with s.get(
                    url,
                    headers=self._headers,
                    proxies=self._proxies,
                    stream=True,
                ) as resp:
                    if resp.status_code != 200:
                        print(resp.json())
                        continue
                    b = resp.content
                    img = Image.open(BytesIO(b))
                    raw.paste(im=img, box=(x * tile_width, y * tile_height))
        # 移除黑边
        return raw, raw.crop(raw.getbbox())
