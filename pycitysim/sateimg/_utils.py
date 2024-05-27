import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon


def get_one_point(shp):
    """
    get one point from the shapefile
    """
    first_geometry = shp.geometry.iloc[0]

    # for different types of geometry, get the first point
    if first_geometry.geom_type == "Polygon":
        first_point = first_geometry.exterior.coords[0]
    elif first_geometry.geom_type == "MultiPolygon":
        first_polygon = list(first_geometry.geoms)[0]
        first_point = first_polygon.exterior.coords[0]
    else:
        raise ValueError("Geometry type not supported")

    pointx, pointy = first_point[0], first_point[1]

    return pointx, pointy


def deg2XY(lon_deg, lat_deg, zoom=15):
    """
    The satellite images are tiles and each tile has a unique x and y index.
    """
    # convert the latitude to radians
    lat_rad = np.radians(lat_deg)

    # the total number of the tiles in the x and y direction
    n = 2.0**zoom

    # the x index of the tile
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    # the y index of the tile
    ytile = int(
        (1.0 - np.log(np.tan(lat_rad) + (1 / np.cos(lat_rad))) / np.pi) / 2.0 * n
    )

    return xtile, ytile


def XY2deg(x, y, zoom=15):
    # the total number of the tiles in the x and y direction
    n = 2.0**zoom

    # the longitude of the tile
    lon_deg = x / n * 360.0 - 180.0
    # the latitude of the tile
    lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))
    # convert the latitude to degrees
    lat_deg = np.rad2deg(lat_rad)

    return lat_deg, lon_deg


def compute_tile_coordinates(min_x, max_x, min_y, max_y):
    """
    Batch version of YX2deg
    """
    x_arr = np.arange(min_x, max_x + 1)
    y_arr = np.arange(min_y, max_y + 1)
    lon_arr, lat_arr = XY2deg_batch(x_arr, y_arr)

    return lon_arr, lat_arr, x_arr, y_arr


def XY2deg_batch(x_arr, y_arr, zoom=15):
    """
    Batch version of num2deg
    """
    n = 2.0**zoom
    lon_deg_arr = x_arr / n * 360.0 - 180.0
    lat_rad_arr = np.arctan(np.sinh(np.pi * (1 - 2 * y_arr / n)))
    lat_deg_arr = np.rad2deg(lat_rad_arr)

    return lon_deg_arr, lat_deg_arr


def create_tile_polygons(lon_arr, lat_arr, x_arr, y_arr):
    """
    Create the polygons for each tile
    """
    # create the lon and lat meshgrid
    lon_mesh, lat_mesh = np.meshgrid(lon_arr, lat_arr, indexing="ij")
    x_mesh, y_mesh = np.meshgrid(x_arr, y_arr, indexing="ij")

    # create the polygons
    vertices = np.array(
        [
            lon_mesh[:-1, :-1],
            lat_mesh[:-1, :-1],
            lon_mesh[1:, :-1],
            lat_mesh[1:, :-1],
            lon_mesh[1:, 1:],
            lat_mesh[1:, 1:],
            lon_mesh[:-1, 1:],
            lat_mesh[:-1, 1:],
        ]
    )
    vertices = vertices.reshape(4, 2, -1)
    vertices = np.transpose(vertices, axes=(2, 0, 1))
    polygons = [Polygon(p) for p in vertices]

    # create the x and y coordinates
    vertices_x_y = np.array(
        [
            x_mesh[:-1, :-1],
            y_mesh[:-1, :-1],
            x_mesh[1:, :-1],
            y_mesh[1:, :-1],
            x_mesh[1:, 1:],
            y_mesh[1:, 1:],
            x_mesh[:-1, 1:],
            y_mesh[:-1, 1:],
        ]
    )
    vertices_x_y = vertices_x_y.reshape(4, 2, -1)
    vertices_x_y = np.transpose(vertices_x_y, axes=(2, 0, 1))
    y_x = [f"{int(p[0][1])}_{int(p[0][0])}" for p in vertices_x_y]

    # create the GeoDataFrame
    tile_gpd = gpd.GeoDataFrame({"Y_X": y_x}, geometry=polygons, crs="EPSG:4326")

    return tile_gpd


def geometry_to_listXY(geometry):
    """
    Convert the geometries to a list of x and y coordinates,
    which can be used as the index to download the satellite images (tiles).
    """
    # get the bbox of the geometries
    """
    may need to fix, when the box cross the 0 degree longitude
    """
    # get the bbox of the geometries
    min_x, min_y, max_x, max_y = geometry.bounds
    minx, maxy = deg2XY(min_x, min_y)
    maxx, miny = deg2XY(max_x, max_y)

    # compute the coordinates of the tiles
    lon_arr, lat_arr, x_arr, y_arr = compute_tile_coordinates(minx, maxx, miny, maxy)
    tile_gpd = create_tile_polygons(lon_arr, lat_arr, x_arr, y_arr)

    # get the tiles that intersect with the geometries
    intersection = gpd.sjoin(
        tile_gpd,
        gpd.GeoDataFrame(data={"tmp": [0]}, geometry=[geometry], crs="EPSG:4326").drop(
            columns=["tmp"]
        ),
        predicate="intersects",
        how="inner",
    )
    Y_X = list(intersection.Y_X)

    # if there is only one tile, then return all the tiles
    if len(Y_X) < 2:
        for x in range(minx, maxx + 1):
            for y in range(miny, maxy + 1):
                Y_X.append(f"{y}_{x}")

    return Y_X


def get_YX_area(area_shp):
    """
    Get the x and y coordinates of the tiles for the given area.
    """
    # unify the Coordinate Reference System (CRS) of the geometries
    area_shp = area_shp.to_crs(epsg=4326)

    # get the coordinates of the tiles
    geometries = area_shp["geometry"]
    area_shp["Y_X"] = geometries.map(geometry_to_listXY)

    # remove the duplicate tiles
    Y_X = sum(list(area_shp["Y_X"]), [])
    Y_X = sorted(list(set(Y_X)))

    return area_shp, Y_X
