import geopandas as gpd
from shapely.geometry import Polygon
from pycitysim.sateimg import download_sateimgs

# build the area
# Polygon: rectangle, center is (116.4, 39.9), width is 0.1, height is 0.1
area = gpd.GeoDataFrame(
    geometry=[
        Polygon(
            [
                (116.4 - 0.05, 39.9 - 0.05),
                (116.4 + 0.05, 39.9 - 0.05),
                (116.4 + 0.05, 39.9 + 0.05),
                (116.4 - 0.05, 39.9 + 0.05),
            ]
        )
    ],
    crs="EPSG:4326",
)  # type: ignore
print(area)

# download the satellite images
imgs = download_sateimgs(area)
print(imgs)
