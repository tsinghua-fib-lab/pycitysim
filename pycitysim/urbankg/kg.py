from typing import List, Optional, Tuple

from lru import LRU
from pymongo import MongoClient

__all__ = ["UrbanKG"]


class UrbanKG:
    """
    城市知识图谱
    """

    CLASSES = ["Region", "POI", "Cate3", "Brand", "Ba", "Cate2", "Cate1"]
    RELATIONS = [
        "SubCateOf_3to2",
        "RelatedBrand",
        "NearBy",
        "LocateAt",
        "LargeOD",
        "Competitive_zhishi",
        "CoCheckin",
        "BorderBy",
        "SubCateOf_2to1",
        "Brand2Cate1",
        "Brand2Cate2",
        "SubCateOf_3to1",
        "BaServe",
        "SimilarPOIs",
        "Cate3Of",
        "Brand2Cate3",
        "BrandOf",
        "Cate2Of",
        "BelongTo",
        "Cate1Of",
    ]

    def __init__(
        self,
        mongo_uri: str,
        mongo_db: str,
        mongo_entity_coll: str,
        mongo_relation_coll: str,
        cache_size: int = 100,
    ):
        """
        Args:
        - mongo_uri: MongoDB URI
        - mongo_db: MongoDB数据库名
        - mongo_entity_coll: MongoDB实体集合名
        - mongo_relation_coll: MongoDB关系集合名
        - cache_size: LRU缓存大小
        """
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        self._entity_coll_name = mongo_entity_coll
        self._entity_coll = db[mongo_entity_coll]
        self._relation_coll_name = mongo_relation_coll
        self._relation_coll = db[mongo_relation_coll]

        self._entity_cache = LRU(cache_size)  # query key => result
        self._relation_cache = LRU(cache_size)  # query key => result

    def get_entity(self, id: str) -> Optional[dict]:
        """
        查询实体

        Args:
        - id: 实体ID

        Returns:
        - Optional[dict]: 实体，为None表示不存在
        """
        if id in self._entity_cache:
            return self._entity_cache[id]
        result = self._entity_coll.find_one({"id": id})
        if result is not None:
            del result["_id"]
        self._entity_cache[id] = result
        return result

    def query_object(self, subject_id: str, relation: str) -> List[str]:
        """
        根据主体（subject）和关系（relation）查询客体（object）

        Args:
        - subject_id: 主体ID
        - relation: 关系

        Returns
        - List[str]: 客体ID列表
        """
        key = (subject_id, relation, "")
        if key in self._relation_cache:
            return self._relation_cache[key]
        result = list(
            self._relation_coll.aggregate(
                [
                    {
                        "$match": {
                            "subject": subject_id,
                            "relation": relation,
                        }
                    },
                    {
                        "$lookup": {
                            "from": self._entity_coll_name,
                            "localField": "object",
                            "foreignField": "id",
                            "as": "object",
                        }
                    },
                    {"$unwind": {"path": "$object"}},
                    {"$project": {"object": 1}},
                ]
            )
        )
        objects = [r["object"] for r in result]
        for obj in objects:
            del obj["_id"]
        self._relation_cache[key] = objects
        return objects

    def query_subject(self, object_id: str, relation: str) -> List[str]:
        """
        根据客体（object）和关系（relation）查询主体（subject）

        Args:
        - object_id: 客体ID
        - relation: 关系

        Returns
        - List[str]: 主体ID列表
        """
        key = ("", relation, object_id)
        if key in self._relation_cache:
            return self._relation_cache[key]
        result = list(
            self._relation_coll.aggregate(
                [
                    {
                        "$match": {
                            "relation": relation,
                            "object": object_id,
                        }
                    },
                    {
                        "$lookup": {
                            "from": self._entity_coll_name,
                            "localField": "subject",
                            "foreignField": "id",
                            "as": "subject",
                        }
                    },
                    {"$unwind": {"path": "$subject"}},
                    {"$project": {"subject": 1}},
                ]
            )
        )
        subjects = [r["subject"] for r in result]
        for sub in subjects:
            del sub["_id"]
        self._relation_cache[key] = subjects
        return subjects

    def explore(self, subject_id: str, relations: List[str]) -> List[Tuple[str, dict]]:
        """
        根据主体（subject）和要探索的关系列表（relations）查询所有有关的客体（object）

        Args:
        - subject_id: 主体ID
        - relations: 要探索的关系列表

        Returns:
        - List[Tuple[str, dict]]: 结果列表，Tuple第一项为关系，第二项为客体
        """
        key = (subject_id, tuple(relations))
        if key in self._relation_cache:
            return self._relation_cache[key]
        result = list(
            self._relation_coll.aggregate(
                [
                    {
                        "$match": {
                            "subject": subject_id,
                            "relation": {"$in": relations},
                        }
                    },
                    {
                        "$lookup": {
                            "from": self._entity_coll_name,
                            "localField": "object",
                            "foreignField": "id",
                            "as": "object",
                        }
                    },
                    {"$unwind": {"path": "$object"}},
                    {"$project": {"relation": 1, "object": 1}},
                ]
            )
        )
        objects = [(r["relation"], r["object"]) for r in result]
        for _, obj in objects:
            del obj["_id"]
        self._relation_cache[key] = objects

        return objects
