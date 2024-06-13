import geopandas as gpd
from shapely.geometry import Polygon
from pycitysim.sateimg import download_sateimgs, download_all_tiles

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

imgs, failed = download_all_tiles(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/27659",
    15,
    ["12394_26956", "12394_26957", "12398_26996"],
)
print("imgs:", imgs)
print("failed:", failed)
# save the images
for key, img in imgs.items():
    img.save(f"cache/{key}.jpg")
