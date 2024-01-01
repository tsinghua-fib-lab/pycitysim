from typing import List

__all__ = ["wrap_feature_collection"]


def wrap_feature_collection(features: List[dict], name: str):
    """
    将 GeoJSON Feature 集合包装为 FeatureCollection
    格式按照【如何与可视化团队交互】文档给出

    Args:
    - features: GeoJSON Feature 集合
    - name: FeatureCollection 名称

    Returns:
    - dict: GeoJSON FeatureCollection
    """
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
