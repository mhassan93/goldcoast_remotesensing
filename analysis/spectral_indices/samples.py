import csv
import math

from pyproj import Transformer

from .settings import project_root

sample_columns = ["sample_id", "set", "stratum", "place", "lon", "lat", "reference_label", "reference_confidence",
                  "reference_notes"]


def read_samples(config):
    with (project_root / config["assessment"]["samples"]).open(newline="", encoding="utf-8") as samples_file:
        return list(csv.DictReader(samples_file))


def grid_cell(sample, grid):
    to_grid = Transformer.from_crs("EPSG:4326", grid.crs, always_xy=True)
    x, y = to_grid.transform(float(sample["lon"]), float(sample["lat"]))
    column = math.floor((x - grid.left) / grid.resolution)
    row = math.floor((grid.top - y) / grid.resolution)
    left = grid.left + column * grid.resolution
    top = grid.top - row * grid.resolution
    return row, column, (left, top - grid.resolution, left + grid.resolution, top)


def cell_centre_lonlat(cell_bounds, grid):
    to_lonlat = Transformer.from_crs(grid.crs, "EPSG:4326", always_xy=True)
    left, bottom, right, top = cell_bounds
    return to_lonlat.transform((left + right) / 2, (bottom + top) / 2)
