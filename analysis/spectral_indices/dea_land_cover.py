import math
import os
import time
from datetime import datetime, timezone

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "3")

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.windows import Window

from .acquire import window_bytes
from .export_web import (export_layer_tiles, hex_to_rgb, inside_tile_pixels, palette_bytes, prepare_output_directory,
                         tile_grid)
from .grid import geometry_bounds, polygons_of, read_boundary_lonlat, transform_geometry
from .settings import load_config, project_root, read_json, shared_results_path, shared_work_path, write_json

coastal_check_points = {
    "Surfers Paradise, ocean 300 m off the beach": (153.4345, -28.0000),
    "Surfers Paradise, beach sand east of the esplanade": (153.4318, -28.0000),
    "Main Beach, ocean": (153.4335, -27.9750),
    "Gold Coast Seaway": (153.4280, -27.9390),
    "South Stradbroke Island": (153.4230, -27.8600),
    "Broadwater": (153.4150, -27.9600),
    "Southern Moreton Bay near Jumpinpin": (153.4400, -27.7400),
    "Burleigh Heads, ocean": (153.4600, -28.0870),
    "Coolangatta, ocean": (153.5450, -28.1650),
    "Tweed River, New South Wales": (153.5300, -28.1900),
    "Hinze Dam": (153.2850, -28.0480),
    "Logan River at the northern boundary": (153.2800, -27.7000),
}


def mosaic_url(config, year):
    return config["assessment"]["dea_level3_mosaic"].format(year=year)


def albers_boundary(config):
    transformer = Transformer.from_crs(config["study_area"]["boundary_crs"], config["dea_land_cover"]["crs"], always_xy=True)
    geometry = transform_geometry(read_boundary_lonlat(config), transformer)
    return geometry, transformer.get_last_used_operation()


def mercator_boundary(config):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    return transform_geometry(read_boundary_lonlat(config), transformer)


def update_dea_manifest(stage, details):
    path = shared_results_path("dea_land_cover", "processing_manifest.json")
    manifest = read_json(path) if path.exists() else {}
    manifest[stage] = {"completed": datetime.now(timezone.utc).isoformat(timespec="seconds"), **details}
    write_json(path, manifest)


def check_mosaic(mosaic, settings, year):
    problems = []
    if mosaic.crs.to_string() != settings["crs"]:
        problems.append(f"CRS {mosaic.crs}")
    if abs(mosaic.res[0] - settings["resolution"]) > 1e-9 or abs(mosaic.res[1] - settings["resolution"]) > 1e-9:
        problems.append(f"resolution {mosaic.res}")
    if mosaic.nodata != settings["nodata"] or mosaic.dtypes[0] != "uint8":
        problems.append(f"nodata {mosaic.nodata}, type {mosaic.dtypes[0]}")
    if problems:
        raise ValueError(f"DEA {year} mosaic does not match the configured source: {', '.join(problems)}")


def read_source_window(config, year):
    settings = config["dea_land_cover"]
    cache_path = shared_work_path("dea_land_cover", f"level3_{year}.tif")
    if cache_path.exists():
        with rasterio.open(cache_path) as cached:
            return cached.read(1), cached.transform, cached.crs, read_json(cache_path.with_suffix(".json"))
    boundary, _ = albers_boundary(config)
    min_x, min_y, max_x, max_y = geometry_bounds(boundary)
    margin = settings["source_margin_m"]
    started = time.time()
    with rasterio.open("/vsicurl/" + mosaic_url(config, year)) as mosaic:
        check_mosaic(mosaic, settings, year)
        resolution = mosaic.res[0]
        column_start = math.floor((min_x - margin - mosaic.transform.c) / resolution)
        column_end = math.ceil((max_x + margin - mosaic.transform.c) / resolution)
        row_start = math.floor((mosaic.transform.f - (max_y + margin)) / resolution)
        row_end = math.ceil((mosaic.transform.f - (min_y - margin)) / resolution)
        window = Window(column_start, row_start, column_end - column_start, row_end - row_start)
        data = mosaic.read(1, window=window)
        transform = mosaic.window_transform(window)
        crs = mosaic.crs
        details = {"window": {"column": column_start, "row": row_start, "width": data.shape[1], "height": data.shape[0]},
                   "compressed_bytes_read": window_bytes(mosaic, window),
                   "mosaic_size": [mosaic.width, mosaic.height], "seconds": round(time.time() - started, 1)}
    profile = {"driver": "GTiff", "width": data.shape[1], "height": data.shape[0], "count": 1, "dtype": "uint8",
               "crs": crs, "transform": transform, "nodata": settings["nodata"], "compress": "deflate", "tiled": True,
               "blockxsize": 256, "blockysize": 256}
    with rasterio.open(cache_path, "w", **profile) as cache:
        cache.write(data[None])
    write_json(cache_path.with_suffix(".json"), details)
    return data, transform, crs, details


def export_dea_tiles(config=None):
    config = config or load_config()
    settings = config["dea_land_cover"]
    started = time.time()
    output_directory = prepare_output_directory(settings["output"])
    bounds = geometry_bounds(read_boundary_lonlat(config))
    boundary_albers, albers_operation = albers_boundary(config)
    boundary_mercator = mercator_boundary(config)
    class_values = [entry["value"] for entry in settings["classes"]]
    class_names = {entry["value"]: entry["name"] for entry in settings["classes"]}
    palette = palette_bytes({entry["value"]: hex_to_rgb(entry["color"]) for entry in settings["classes"]})
    pixel_area_km2 = settings["resolution"] ** 2 / 1e6
    report = {}
    for year in settings["years"]:
        data, transform, crs, source_details = read_source_window(config, year)
        unexpected = sorted(set(np.unique(data).tolist()) - set(class_values) - {settings["nodata"]})
        if unexpected:
            raise ValueError(f"DEA {year} contains values outside the Level 3 classes: {unexpected}")
        inside = rasterize([(boundary_albers, 1)], out_shape=data.shape, transform=transform, fill=0,
                           all_touched=False, dtype="uint8").astype(bool)
        layer = {"data": data, "data_inside_boundary": np.where(inside, data, settings["nodata"]).astype(np.uint8),
                 "categorical": True, "nodata": settings["nodata"], "transform": transform, "crs": crs, "palette": palette}
        tiles = export_layer_tiles(layer, output_directory / str(year), (settings["min_zoom"], settings["max_zoom"]),
                                   bounds, settings["resolution"], boundary_mercator)
        inside_values = data[inside]
        report[year] = {
            "source": mosaic_url(config, year),
            "source_window": source_details,
            "source_pixels_inside_boundary": int(inside.sum()),
            "class_area_inside_boundary_km2": {class_names[value]: round(int((inside_values == value).sum()) * pixel_area_km2, 2)
                                               for value in class_values},
            "no_data_area_inside_boundary_km2": round(int((inside_values == settings["nodata"]).sum()) * pixel_area_km2, 2),
            **tiles,
        }
        print(f"DEA {year}: {tiles['tiles']} tiles, {tiles['bytes'] / 1e6:.2f} MB", flush=True)
    metadata = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "DEA Land Cover Level 3, clipped to the City of Gold Coast",
        "product": "DEA Land Cover (Landsat), ga_ls_landcover_class_cyear_3",
        "version": settings["version"],
        "licence": "CC BY 4.0",
        "attribution": "DEA Land Cover v2.0.0 © Commonwealth of Australia (Geoscience Australia), CC BY 4.0",
        "changes": "Clipped to the City of Gold Coast boundary and re-tiled by this project. Class codes and colours unchanged.",
        "source_template": config["assessment"]["dea_level3_mosaic"],
        "years": settings["years"],
        "path": "{year}/{z}/{x}/{y}.png",
        "tile_size": 256,
        "min_zoom": settings["min_zoom"],
        "max_zoom": settings["max_zoom"],
        "bounds": list(bounds),
        "palette_index": "Each opaque pixel's palette index is its official Level 3 class code. Index 0 is transparent.",
        "classes": settings["classes"],
    }
    write_json(output_directory / "layers.json", metadata)
    total_bytes = sum(entry["bytes"] for entry in report.values()) + (output_directory / "layers.json").stat().st_size
    details = {
        "output": settings["output"],
        "zooms": [settings["min_zoom"], settings["max_zoom"]],
        "boundary_to_source_crs": albers_operation.description,
        "boundary_to_tile_grid": "Boundary coordinates projected to EPSG:3857 as given, the same way MapLibre draws the outline",
        "clipping": "A tile pixel is kept only if its centre lies inside the boundary, tested on every zoom's own tile grid. "
                    "Enlarged zooms take the class at the pixel centre (nearest); reduced zooms take the most common "
                    "class of the source pixels whose centres lie inside the boundary (mode).",
        "years": report,
        "total_bytes": total_bytes,
        "total_files": sum(entry["tiles"] for entry in report.values()) + 1,
        "seconds": round(time.time() - started, 1),
    }
    update_dea_manifest("dea-tiles", details)
    print(f"total {total_bytes / 1e6:.2f} MB in {details['total_files']} files")
    return details


def points_inside_polygon(xs, ys, geometry, chunk=1000):
    inside = np.zeros(xs.shape, dtype=bool)
    for polygon in polygons_of(geometry):
        for ring in polygon:
            vertices = np.asarray(ring, dtype=np.float64)
            x1, y1, x2, y2 = vertices[:-1, 0], vertices[:-1, 1], vertices[1:, 0], vertices[1:, 1]
            for start in range(0, xs.size, chunk):
                px, py = xs[start:start + chunk, None], ys[start:start + chunk, None]
                straddles = (y1 > py) != (y2 > py)
                with np.errstate(divide="ignore", invalid="ignore"):
                    crossing_x = (x2 - x1) * (py - y1) / (y2 - y1) + x1
                inside[start:start + chunk] ^= (straddles & (px < crossing_x)).sum(axis=1) % 2 == 1
    return inside


def read_tile_mosaic(layer_directory, bounds, zoom, expected_colours):
    first_column, first_row, transform, shape = tile_grid(bounds, zoom)
    indices = np.zeros(shape, dtype=np.uint8)
    palette_problems = []
    for row in range(shape[0] // 256):
        for column in range(shape[1] // 256):
            path = layer_directory / str(zoom) / str(first_column + column) / f"{first_row + row}.png"
            with Image.open(path) as image:
                block = np.asarray(image)
                palette = image.getpalette()
                if image.mode != "P" or image.info.get("transparency") != 0:
                    palette_problems.append(f"{path.name}: mode {image.mode}, transparency {image.info.get('transparency')}")
                for value in np.unique(block[block > 0]).tolist():
                    if tuple(palette[value * 3:value * 3 + 3]) != expected_colours.get(value):
                        palette_problems.append(f"{zoom}/{first_column + column}/{first_row + row}: index {value}")
            indices[row * 256:(row + 1) * 256, column * 256:(column + 1) * 256] = block
    return indices, transform, palette_problems


def pixel_centres(transform, rows, columns):
    return transform.c + (columns + 0.5) * transform.a, transform.f + (rows + 0.5) * transform.e


def verify_dea_tiles(config=None, sample_size=20000, remote_sample_size=500):
    config = config or load_config()
    settings = config["dea_land_cover"]
    output_directory = project_root / settings["output"]
    bounds = geometry_bounds(read_boundary_lonlat(config))
    boundary_mercator = mercator_boundary(config)
    to_albers = Transformer.from_crs("EPSG:3857", settings["crs"], always_xy=True)
    to_mercator = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    expected_colours = {entry["value"]: hex_to_rgb(entry["color"]) for entry in settings["classes"]}
    rng = np.random.default_rng(2026)
    report = {"sample_size_per_zoom": sample_size, "years": {}}
    for year in settings["years"]:
        data, source_transform, _, _ = read_source_window(config, year)
        year_report = {"zooms": {}, "coastal_points": {}}
        for zoom in range(settings["min_zoom"], settings["max_zoom"] + 1):
            indices, transform, palette_problems = read_tile_mosaic(output_directory / str(year), bounds, zoom, expected_colours)
            touched = rasterize([(boundary_mercator, 1)], out_shape=indices.shape, transform=transform, fill=0,
                                all_touched=True, dtype="uint8").astype(bool)
            opaque = indices > 0
            sample = rng.choice(indices.size, size=min(sample_size, indices.size), replace=False)
            rows, columns = np.unravel_index(sample, indices.shape)
            xs, ys = pixel_centres(transform, rows, columns)
            centre_inside = points_inside_polygon(xs, ys, boundary_mercator)
            zoom_report = {
                "tile_pixels": int(indices.size),
                "opaque_pixels": int(opaque.sum()),
                "opaque_pixels_not_touching_boundary": int((opaque & ~touched).sum()),
                "sampled_pixels": int(sample.size),
                "sampled_outside_but_opaque": int((~centre_inside & opaque[rows, columns]).sum()),
                "sampled_inside_but_transparent": int((centre_inside & ~opaque[rows, columns]).sum()),
                "palette_problems": palette_problems[:5],
                "values_present": sorted(np.unique(indices[opaque]).tolist()),
            }
            if zoom >= 13:
                opaque_rows, opaque_columns = np.nonzero(opaque)
                xs, ys = pixel_centres(transform, opaque_rows, opaque_columns)
                albers_x, albers_y = to_albers.transform(xs, ys)
                source_columns = np.floor((np.asarray(albers_x) - source_transform.c) / source_transform.a).astype(int)
                source_rows = np.floor((np.asarray(albers_y) - source_transform.f) / source_transform.e).astype(int)
                padded = np.pad(data, 1, constant_values=settings["nodata"])
                neighbourhood = np.stack([padded[source_rows + 1 + dr, source_columns + 1 + dc]
                                          for dr in (-1, 0, 1) for dc in (-1, 0, 1)])
                centre_values = data[source_rows, source_columns]
                tile_values = indices[opaque_rows, opaque_columns]
                matches = tile_values == centre_values
                uniform = np.all(neighbourhood == centre_values[None], axis=0)
                from_neighbourhood = np.any(neighbourhood == tile_values[None], axis=0)
                zoom_report["interior_comparison"] = {
                    "opaque_pixels_compared": int(matches.size),
                    "match_source_class_at_pixel_centre": round(float(matches.mean()), 6),
                    "pixels_with_uniform_3x3_source": int(uniform.sum()),
                    "match_where_source_3x3_uniform": round(float(matches[uniform].mean()), 6),
                    "mismatches_where_source_3x3_uniform": int((~matches[uniform]).sum()),
                    "mismatches_with_class_from_source_3x3": int((~matches & from_neighbourhood).sum()),
                    "mismatches_with_class_not_in_source_3x3": int((~matches & ~from_neighbourhood).sum()),
                }
                transparent_inside = centre_inside & ~opaque[rows, columns]
                sampled_x, sampled_y = pixel_centres(transform, rows[transparent_inside], columns[transparent_inside])
                sampled_albers_x, sampled_albers_y = to_albers.transform(sampled_x, sampled_y)
                sampled_source = data[
                    np.floor((np.asarray(sampled_albers_y) - source_transform.f) / source_transform.e).astype(int),
                    np.floor((np.asarray(sampled_albers_x) - source_transform.c) / source_transform.a).astype(int)]
                zoom_report["sampled_inside_but_transparent_with_source_no_data"] = int(
                    (sampled_source == settings["nodata"]).sum())
            year_report["zooms"][zoom] = zoom_report
            for name, (longitude, latitude) in coastal_check_points.items():
                x, y = to_mercator.transform(longitude, latitude)
                column = int((x - transform.c) // transform.a)
                row = int((y - transform.f) // transform.e)
                centre_x, centre_y = pixel_centres(transform, np.array([row]), np.array([column]))
                expected_inside = bool(points_inside_polygon(centre_x, centre_y, boundary_mercator)[0])
                value = int(indices[row, column])
                entry = year_report["coastal_points"].setdefault(name, {"inside_boundary_at_pixel_centre": {}, "tile_value": {}})
                entry["inside_boundary_at_pixel_centre"][zoom] = expected_inside
                entry["tile_value"][zoom] = value
        with rasterio.open("/vsicurl/" + mosaic_url(config, year)) as mosaic:
            sample_rows = rng.integers(0, data.shape[0], remote_sample_size)
            sample_columns = rng.integers(0, data.shape[1], remote_sample_size)
            points = [(source_transform.c + (column + 0.5) * source_transform.a,
                       source_transform.f + (row + 0.5) * source_transform.e)
                      for row, column in zip(sample_rows, sample_columns)]
            remote = np.array([value[0] for value in mosaic.sample(points)])
        year_report["cached_window_matches_remote_mosaic"] = {
            "points": remote_sample_size, "matching": int((remote == data[sample_rows, sample_columns]).sum())}
        year_report["coastal_points_consistent"] = all(
            (value > 0) == entry["inside_boundary_at_pixel_centre"][zoom]
            for entry in year_report["coastal_points"].values() for zoom, value in entry["tile_value"].items())
        report["years"][year] = year_report
        worst = min(zoom["interior_comparison"]["match_where_source_3x3_uniform"]
                    for zoom in year_report["zooms"].values() if "interior_comparison" in zoom)
        print(f"DEA {year}: outside opaque {sum(z['opaque_pixels_not_touching_boundary'] for z in year_report['zooms'].values())}, "
              f"sampled mismatches {sum(z['sampled_outside_but_opaque'] + z['sampled_inside_but_transparent'] for z in year_report['zooms'].values())}, "
              f"uniform-neighbourhood match {worst:.6f}, coastal points consistent {year_report['coastal_points_consistent']}, "
              f"remote check {year_report['cached_window_matches_remote_mosaic']}", flush=True)
    report["all_checks_pass"] = all(
        zoom["opaque_pixels_not_touching_boundary"] == 0 and zoom["sampled_outside_but_opaque"] == 0
        and not zoom["palette_problems"] and set(zoom["values_present"]) <= set(expected_colours)
        and zoom.get("interior_comparison", {}).get("mismatches_where_source_3x3_uniform", 0) == 0
        and zoom.get("interior_comparison", {}).get("mismatches_with_class_not_in_source_3x3", 0) == 0
        and zoom.get("sampled_inside_but_transparent_with_source_no_data",
                     zoom["sampled_inside_but_transparent"]) == zoom["sampled_inside_but_transparent"]
        for year_report in report["years"].values() for zoom in year_report["zooms"].values()
    ) and all(year_report["coastal_points_consistent"]
              and year_report["cached_window_matches_remote_mosaic"]["matching"] == remote_sample_size
              for year_report in report["years"].values())
    write_json(shared_results_path("dea_land_cover", "verification.json"), report)
    update_dea_manifest("dea-verify", {"output": "analysis/results/dea_land_cover/verification.json",
                                       "all_checks_pass": report["all_checks_pass"]})
    print("all checks pass:", report["all_checks_pass"])
    return report
