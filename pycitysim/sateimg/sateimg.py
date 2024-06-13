import time
from io import BytesIO
from typing import Dict, List, Tuple
import geopandas as gpd

import numpy as np
import requests
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes

from ._utils import get_YX_area, XY2deg

__all__ = ["download_sateimgs", "download_all_tiles"]


def _download_one_tile(args):
    """
    Download the tile for the given x and y coordinates.
    From Esri living atlas, the token is required to download the tiles.

    Depending on the API of the tile server.
    """
    # args
    base_url, Z, X, Y = args
    base_url = base_url.rstrip("/")

    # the url of the tile
    # base_url = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/41468/15/"
    # url = base_url + str(Y) + "/" + str(X) + "?token=123"
    url = f"{base_url}/{Z}/{Y}/{X}"

    # the filename of the tile
    filename = str(Y) + "_" + str(X)

    try:
        try:
            response = requests.get(url)
            response.raise_for_status()
            img_bytes = BytesIO(response.content)
            return filename, img_bytes
        except:
            time.sleep(1)
            response = requests.get(url)
            response.raise_for_status()
            img_bytes = BytesIO(response.content)
            return filename, img_bytes
    except:
        return filename


def download_all_tiles(
    base_url: str, Z: int, Y_X: List[str]
) -> Tuple[Dict[str, Image.Image], List[str]]:
    """
    Download all the tiles for the given x and y coordinates.
    From Esri living atlas, the token is required to download the tiles.

    The tiles are downloaded into the given directory.

    Args:
    - base_url (str): the base url of the tile server.
    - Z (int): the zoom level.
    - Y_X (List[str]): the list of y_x coordinates.

    Returns:
    - cached_tiles (Dict[str, Image.Image]): the cached tiles.
    - fail_tile_list (List[str]): the list of failed tiles.
    """

    # the arguments for the download_one_tile function
    tile_args = [
        (base_url, int(Z), int(X), int(Y)) for Y, X in [y_x.split("_") for y_x in Y_X]
    ]

    # download the tiles
    cached_tiles = {}
    fail_tile_list = []

    # sequential version
    for arg in tile_args:
        result = _download_one_tile(arg)
        if isinstance(result, tuple):
            tile_no, img = result
            cached_tiles[tile_no] = Image.open(img)
        elif isinstance(result, str):
            fail_tile_list.append(result)

    return cached_tiles, fail_tile_list


def _concat_img_one_region(args):
    """
    Concatenate the tiles to obtain the regional satellite images.
    """
    # args
    region, tiles, files = args

    # the region should not be too large
    if len(tiles) < 20000:
        # get the x and y coordinates of the tiles
        ys, xs = zip(*[(int(i.split("_")[0]), int(i.split("_")[1])) for i in tiles])

        # get the min and max x and y coordinates
        row_min, col_min, row_max, col_max = min(ys), min(xs), max(ys), max(xs)

        # generate the mask
        mask_width = col_max - col_min + 1
        mask_height = row_max - row_min + 1

        mask_whole = np.zeros([mask_height * 256, mask_width * 256, 3], dtype=np.int32)

        # the pixel coordinates
        pixel_coords = []
        for tile in tiles:
            try:
                # read the tile
                img_temp = files[tile]

                # get the tile's x and y coordinates
                row, col = [int(x) for x in tile.split("_")]

                # convert the tile's x and y coordinates to the longitude and latitude
                minlat, minlon = XY2deg(col, row, 15)
                maxlat, maxlon = XY2deg(col + 1, row + 1, 15)

                if region.iloc[0].geometry.geom_type != "MultiPolygon":
                    # if the region is not a multi-polygon
                    for coord in region.iloc[0].geometry.exterior.coords:
                        # convert the longitude and latitude to the pixel coordinates, offset
                        x = (coord[0] - minlon) * (256 / (maxlon - minlon))
                        y = (coord[1] - minlat) * (256 / (maxlat - minlat))

                        # convert the pixel coordinates to the regional pixel coordinates, overall
                        temp_x, temp_y = (
                            x + (col - col_min) * 256,
                            y + (row - row_min) * 256,
                        )
                        if temp_x > 256 * mask_width:
                            temp_x = 256 * mask_width
                        if temp_y > 256 * mask_height:
                            temp_y = 256 * mask_height
                        if temp_x < 0:
                            temp_x = 0
                        if temp_y < 0:
                            temp_y = 0

                        # store the pixel coordinates
                        pixel_coords.append((temp_x, temp_y))
                else:
                    # if the region is a multi-polygon
                    for polygon in region.iloc[0].geometry.geoms:
                        for coord in polygon.exterior.coords:
                            # convert the longitude and latitude to the pixel coordinates, offset
                            x = (coord[0] - minlon) * (256 / (maxlon - minlon))
                            y = (coord[1] - minlat) * (256 / (maxlat - minlat))

                            # convert the pixel coordinates to the regional pixel coordinates, overall
                            temp_x, temp_y = (
                                x + (col - col_min) * 256,
                                y + (row - row_min) * 256,
                            )
                            if temp_x > 256 * mask_width:
                                temp_x = 256 * mask_width
                            if temp_y > 256 * mask_height:
                                temp_y = 256 * mask_height

                            if temp_x < 0:
                                temp_x = 0
                            if temp_y < 0:
                                temp_y = 0

                            # store the pixel coordinates
                            pixel_coords.append((temp_x, temp_y))

                mask_whole[
                    (row - row_min) * 256 : (row - row_min + 1) * 256,
                    (col - col_min) * 256 : (col - col_min + 1) * 256,
                    :,
                ] = img_temp
            except:
                continue

        # fill the holes in the mask
        if mask_whole.sum() != 0:
            # convert the mask to the image
            im = np.uint8(mask_whole)
            im_zero = Image.new("L", (mask_width * 256, mask_height * 256), 0)
            draw = ImageDraw.Draw(im_zero)
            for i in range(len(pixel_coords)):
                draw.line(
                    [pixel_coords[i], pixel_coords[(i + 1) % len(pixel_coords)]],
                    fill="red",
                    width=5,
                )
            filled_mask = binary_fill_holes(im_zero)

            # save the image
            im = im * filled_mask.reshape(filled_mask.shape[0], filled_mask.shape[1], 1)
            im = Image.fromarray(np.uint8(im))
            return int(region.index[0]), im
        else:
            return int(region.index[0])

    else:
        return int(region.index[0])


def _concatenate_tiles(
    region_list, area_shp: gpd.GeoDataFrame, cached_tiles: Dict[str, Image.Image]
):
    """
    Concatenate the tiles to obtain all the regional satellite images given the area.
    """

    # list of region idx
    region_list = sorted(region_list)

    # list of the arguments
    args = [
        (
            area_shp[area_shp.index == i],
            area_shp.loc[area_shp.index == i, "Y_X"].item(),
            {
                key: cached_tiles[key]
                for key in area_shp.loc[area_shp.index == i, "Y_X"].item()
                if key in cached_tiles
            },
        )
        for i in region_list
    ]

    # concatenate the tiles
    regional_imgs = {}
    fail_region_list = []

    # sequential version
    for arg in args:
        result = _concat_img_one_region(arg)
        if isinstance(result, tuple):
            idx, img = result
            regional_imgs[idx] = img
        else:
            fail_region_list.append(result)

    return regional_imgs, fail_region_list


def download_sateimgs(
    area_shp: gpd.GeoDataFrame,
    base_url: str = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/41468",
    Z: int = 15,
) -> Dict[int, Image.Image]:
    """
    Download the satellite images for the given area from Esri living atlas.

    Args:
    - area_shp (gpd.GeoDataFrame): the areas to download the satellite images.

    Returns:
    - regional_imgs (Dict[int, Image.Image]): the regional satellite images.
    """

    # coordinate system
    area_shp = area_shp.to_crs(epsg=4326)

    # get the x and y coordinates of the tiles
    area_shp, Y_X = get_YX_area(area_shp)

    # download the tiles
    cached_tiles: Dict[str, Image.Image] = {}
    remaining = Y_X
    while remaining != []:
        cached_tiles_tmp, fail_tile_list = download_all_tiles(base_url, Z, remaining)
        cached_tiles.update(cached_tiles_tmp)
        remaining = fail_tile_list

    # concatenate the tiles to obtain the regional satellite images
    regional_imgs = {}
    remaining = area_shp.index.to_list()
    while remaining != []:
        regional_imgs_tmp, fail_region_list = _concatenate_tiles(
            remaining,
            area_shp,
            cached_tiles,
        )
        regional_imgs.update(regional_imgs_tmp)
        remaining = fail_region_list

    return regional_imgs
