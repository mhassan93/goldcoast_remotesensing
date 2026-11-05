import json
import math
from dataclasses import dataclass

from affine import Affine
from pyproj import Transformer
from rasterio.features import rasterize

from .settings import project_root


@dataclass(frozen=True)
class AnalysisGrid:
    crs: str
    resolution: float
    left: float
    top: float
    width: int
    height: int

    @property
    def transform(self):
        return Affine(self.resolution, 0, self.left, 0, -self.resolution, self.top)

    @property
    def right(self):
        return self.left + self.width * self.resolution

    @property
    def bottom(self):
        return self.top - self.height * self.resolution

    def describe(self):
        return {
            "crs": self.crs,
            "resolution_m": self.resolution,
            "bounds": [self.left, self.bottom, self.right, self.top],
            "width": self.width,
            "height": self.height,
            "transform": list(self.transform)[:6],
        }


def read_boundary_lonlat(config):
    boundary_file = project_root / config["study_area"]["boundary"]
    collection = json.loads(boundary_file.read_text(encoding="utf-8"))
    if len(collection["features"]) != 1:
        raise ValueError(f"Expected one boundary feature in {boundary_file}")
    return collection["features"][0]["geometry"]


def polygons_of(geometry):
    return [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]


def geometry_bounds(geometry):
    xs = [point[0] for polygon in polygons_of(geometry) for ring in polygon for point in ring]
    ys = [point[1] for polygon in polygons_of(geometry) for ring in polygon for point in ring]
    return min(xs), min(ys), max(xs), max(ys)


def boundary_transformer(config):
    return Transformer.from_crs(config["study_area"]["boundary_crs"], config["grid"]["crs"], always_xy=True)


def transform_geometry(geometry, transformer):
    transformed_polygons = []
    for polygon in polygons_of(geometry):
        transformed_rings = []
        for ring in polygon:
            xs, ys = transformer.transform([point[0] for point in ring], [point[1] for point in ring])
            transformed_rings.append([[x, y] for x, y in zip(xs, ys)])
        transformed_polygons.append(transformed_rings)
    return {"type": "MultiPolygon", "coordinates": transformed_polygons}


def build_grid(config):
    transformer = boundary_transformer(config)
    boundary = transform_geometry(read_boundary_lonlat(config), transformer)
    resolution = config["grid"]["resolution"]
    min_x, min_y, max_x, max_y = geometry_bounds(boundary)
    left = math.floor(min_x / resolution) * resolution
    bottom = math.floor(min_y / resolution) * resolution
    right = math.ceil(max_x / resolution) * resolution
    top = math.ceil(max_y / resolution) * resolution
    grid = AnalysisGrid(
        crs=config["grid"]["crs"],
        resolution=resolution,
        left=left,
        top=top,
        width=round((right - left) / resolution),
        height=round((top - bottom) / resolution),
    )
    return grid, boundary, transformer


def boundary_mask(grid, boundary):
    burned = rasterize(
        [(boundary, 1)],
        out_shape=(grid.height, grid.width),
        transform=grid.transform,
        fill=0,
        all_touched=False,
        dtype="uint8",
    )
    return burned.astype(bool)
