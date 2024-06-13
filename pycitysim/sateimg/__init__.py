"""
卫星影像数据下载
Satellite image data download
"""

from .sateimg import download_sateimgs, download_all_tiles

__all__ = ["download_sateimgs", "download_all_tiles"]
