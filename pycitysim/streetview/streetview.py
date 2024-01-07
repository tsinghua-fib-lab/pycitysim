from io import BytesIO
from typing import Optional, Tuple

from obs import ObsClient
from PIL import Image
from pymongo import MongoClient

__all__ = ["StreetViews"]


class StreetViews:
    """
    街景数据API
    """

    def __init__(
        self,
        mongo_uri: str,
        mongo_db: str,
        mongo_coll: str,
        obs_ak: str,
        obs_sk: str,
        obs_endpoint: str,
        obs_bucket: str,
    ):
        """
        Args:
        - mongo_uri (str): MongoDB连接URI
        - mongo_db (str): MongoDB数据库名称
        - mongo_coll (str): MongoDB集合名称
        - obs_ak (str): 华为云OBS Access Key
        - obs_sk (str): 华为云OBS Secret Key
        - obs_endpoint (str): 华为云OBS Endpoint
        - obs_bucket (str): 华为云OBS Bucket
        """
        self._mongo = MongoClient(mongo_uri)[mongo_db][mongo_coll]
        self._obs = ObsClient(
            access_key_id=obs_ak, secret_access_key=obs_sk, server=obs_endpoint
        )
        self._bucket = obs_bucket

    def query(
        self,
        center: Tuple[float, float],
        radius: float,
        limit: Optional[int] = None,
    ):
        """
        查询center点指定半径内的街景数据

        Args:
        - center (lng, lat): WGS84经纬度坐标
        - radius (float): 半径（单位：m）
        - limit (int): 返回数量限制

        Returns:
        - List[dict]: 街景数据列表（含经纬度、朝向角度、图片）
        """
        stage = {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": center},
                "distanceField": "data.distance",
                "maxDistance": radius,
                "spherical": True,
            }
        }
        if limit is not None:
            stage["$geoNear"]["num"] = limit
        result = self._mongo.aggregate([stage])
        all = []
        for one in result:
            one = one["data"]
            del one["external"]
            for image in one["images"]:
                obj = image["object"]
                download = self._obs.getObject(
                    self._bucket, obj, loadStreamInMemory=True
                )
                if download.errorCode is not None:
                    raise Exception(download.errorMessage)
                img = Image.open(BytesIO(download.body.buffer))  # type: ignore
                image["image"] = img
            all.append(one)
        return all
