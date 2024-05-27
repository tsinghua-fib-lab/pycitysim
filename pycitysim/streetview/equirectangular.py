from typing import Union

import cv2
import numpy as np
from PIL import Image

from .baidu import BaiduStreetView
from .google import GoogleStreetView

__all__ = ["Equirectangular"]


class Equirectangular:
    """
    用于将等距柱状全景图分割成普通透视图

    python tool to split equirectangular panorama into normal perspective view.

    修改自(Modified From)：https://github.com/fuenwang/Equirec2Perspec/tree/master

    MIT License

    Copyright (c) 2021 Fu-En Wang

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """

    def __init__(self, sv: Union[BaiduStreetView, GoogleStreetView]):
        self._img = self.pil2cv(sv.panorama)
        self._heading = sv.heading
        [self._height, self._width, _] = self._img.shape

    @staticmethod
    def pil2cv(img: Image.Image):
        """
        PIL.Image.Image -> OpenCV
        """
        cv2_img = np.array(img)
        cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_RGB2BGR)
        return cv2_img

    @staticmethod
    def cv2pil(img: np.ndarray):
        """
        OpenCV -> PIL.Image.Image
        """
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img)
        return pil_img

    @staticmethod
    def _xyz2lonlat(xyz):
        atan2 = np.arctan2
        asin = np.arcsin

        norm = np.linalg.norm(xyz, axis=-1, keepdims=True)
        xyz_norm = xyz / norm
        x = xyz_norm[..., 0:1]
        y = xyz_norm[..., 1:2]
        z = xyz_norm[..., 2:]

        lon = atan2(x, z)
        lat = asin(y)
        lst = [lon, lat]

        out = np.concatenate(lst, axis=-1)
        return out

    @staticmethod
    def _lonlat2XY(lonlat, shape):
        X = (lonlat[..., 0:1] / (2 * np.pi) + 0.5) * (shape[1] - 1)
        Y = (lonlat[..., 1:] / (np.pi) + 0.5) * (shape[0] - 1)
        lst = [X, Y]
        out = np.concatenate(lst, axis=-1)

        return out

    def get_perspective(
        self, fov: float, heading: float, pitch: float, height: float, width: float
    ):
        """
        全景图透视投影
        Equirectangular to Perspective

        Args:
        - fov: 视野（单位：度）。Field of View (unit: degree)
        - heading: 水平方向朝向角（单位：度），范围为[0, 360]，正东方向为0度，逆时针旋转。Horizontal direction angle (unit: degree), range is [0, 360], 0 degrees is east, counterclockwise rotation.
        - pitch: 俯仰角（单位：度），范围为[-90, 90]，0度为水平方向，90度为垂直向上，-90度为垂直向下。Pitch angle (unit: degree), range is [-90, 90], 0 degrees is the horizontal direction, 90 degrees is vertical up, and -90 degrees is vertical down.
        - height: 输出图像高度。Output image height.
        - width: 输出图像宽度。Output image width.
        """
        heading = -(self._heading + heading + 180)

        f = 0.5 * width * 1 / np.tan(0.5 * fov / 180.0 * np.pi)
        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        K = np.array(
            [
                [f, 0, cx],
                [0, f, cy],
                [0, 0, 1],
            ],
            np.float32,
        )
        K_inv = np.linalg.inv(K)

        x = np.arange(width)
        y = np.arange(height)
        x, y = np.meshgrid(x, y)
        z = np.ones_like(x)
        xyz = np.concatenate([x[..., None], y[..., None], z[..., None]], axis=-1)
        xyz = xyz @ K_inv.T

        y_axis = np.array([0.0, 1.0, 0.0], np.float32)
        x_axis = np.array([1.0, 0.0, 0.0], np.float32)
        R1, _ = cv2.Rodrigues(y_axis * np.radians(heading))
        R2, _ = cv2.Rodrigues(np.dot(R1, x_axis) * np.radians(pitch))
        R = R2 @ R1
        xyz = xyz @ R.T
        lonlat = self._xyz2lonlat(xyz)
        XY = self._lonlat2XY(lonlat, shape=self._img.shape).astype(np.float32)
        persp = cv2.remap(
            self._img,
            XY[..., 0],
            XY[..., 1],
            cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_WRAP,
        )

        return self.cv2pil(persp)
