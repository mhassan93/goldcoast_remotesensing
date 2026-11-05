import math
import shutil
import time
from datetime import datetime, timezone

import numpy as np
import rasterio
from affine import Affine
from PIL import Image
from rasterio.warp import Resampling, reproject

from .composite import index_names
from .grid import geometry_bounds, read_boundary_lonlat
from .manifest import read_manifest, update_manifest
from .settings import load_config, project_root, work_path, write_json

earth_circumference = 2 * math.pi * 6378137


def tile_column(longitude, zoom):
    return math.floor((longitude + 180) / 360 * 2 ** zoom)


def tile_row(latitude, zoom):
    radians = math.radians(latitude)
    return math.floor((1 - math.asinh(math.tan(radians)) / math.pi) / 2 * 2 ** zoom)


def hex_to_rgb(colour):
    return tuple(int(colour[position:position + 2], 16) for position in (1, 3, 5))


def ramp_colours(stops, value_range, steps):
    positions = np.linspace(value_range[0], value_range[1], steps)
    stop_values = [stop[0] for stop in stops]
    channels = np.array([hex_to_rgb(stop[1]) for stop in stops], dtype=np.float64)
    return [tuple(int(round(np.interp(value, stop_values, channels[:, channel]))) for channel in range(3))
            for value in positions]


def palette_bytes(colours_by_index):
    palette = [0] * 768
    for index, colour in colours_by_index.items():
        palette[index * 3:index * 3 + 3] = colour
    return palette


def quantise(values, value_range, steps):
    scaled = np.clip(np.round((values - value_range[0]) / (value_range[1] - value_range[0]) * (steps - 1)), 0, steps - 1)
    indexed = np.where(np.isfinite(values), scaled + 1, 0)
    return indexed.astype(np.uint8)


def resampling_for(zoom, latitude, source_resolution, categorical):
    ground_resolution = earth_circumference / (256 * 2 ** zoom) * math.cos(math.radians(latitude))
    if ground_resolution <= source_resolution:
        return (Resampling.nearest if categorical else Resampling.bilinear), ground_resolution
    return (Resampling.mode if categorical else Resampling.average), ground_resolution


def write_tiles(layer_directory, zoom, first_column, first_row, mosaic, palette):
    sizes = []
    rows, columns = mosaic.shape[0] // 256, mosaic.shape[1] // 256
    for row_offset in range(rows):
        for column_offset in range(columns):
            block = mosaic[row_offset * 256:(row_offset + 1) * 256, column_offset * 256:(column_offset + 1) * 256]
            tile_path = layer_directory / str(zoom) / str(first_column + column_offset) / f"{first_row + row_offset}.png"
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            image = Image.fromarray(block, mode="P")
            image.putpalette(palette)
            image.save(tile_path, optimize=True, transparency=0)
            sizes.append(tile_path.stat().st_size)
    return sizes


def export(config=None):
    config = config or load_config()
    started = time.time()
    web = config["web"]
    output_directory = (project_root / web["output"]).resolve()
    public_data = (project_root / "public" / "data").resolve()
    if public_data not in output_directory.parents:
        raise ValueError(f"Refusing to write web output outside {public_data}")
    if output_directory.exists():
        shutil.rmtree(output_directory)
    west, south, east, north = geometry_bounds(read_boundary_lonlat(config))
    centre_latitude = (south + north) / 2
    with rasterio.open(work_path("classification", "index_rule_classes.tif")) as source:
        classes = source.read(1)
        source_transform, source_crs = source.transform, source.crs
    with rasterio.open(work_path("composite", "index_medians.tif")) as source:
        medians = source.read()
    steps = web["index_colour_steps"]
    layers = {"classes": {"data": classes, "categorical": True, "nodata": 0,
                          "palette": palette_bytes({entry["value"]: hex_to_rgb(entry["color"]) for entry in web["classes"]})}}
    for position, name in enumerate(index_names):
        settings = web["indices"][name]
        colours = ramp_colours(settings["stops"], settings["range"], steps)
        layers[name] = {"data": medians[position], "categorical": False, "nodata": np.nan, "range": settings["range"],
                        "palette": palette_bytes({step + 1: colour for step, colour in enumerate(colours)})}
    report = {}
    for name, layer in layers.items():
        sizes, resampling_by_zoom = [], {}
        for zoom in range(web["min_zoom"], web["max_zoom"] + 1):
            first_column, last_column = tile_column(west, zoom), tile_column(east, zoom)
            first_row, last_row = tile_row(north, zoom), tile_row(south, zoom)
            resolution = earth_circumference / (256 * 2 ** zoom)
            destination_transform = Affine(resolution, 0, -earth_circumference / 2 + first_column * 256 * resolution,
                                           0, -resolution, earth_circumference / 2 - first_row * 256 * resolution)
            shape = ((last_row - first_row + 1) * 256, (last_column - first_column + 1) * 256)
            resampling, ground_resolution = resampling_for(zoom, centre_latitude, config["grid"]["resolution"],
                                                           layer["categorical"])
            destination = np.full(shape, layer["nodata"], dtype=layer["data"].dtype)
            reproject(source=layer["data"], destination=destination, src_transform=source_transform, src_crs=source_crs,
                      src_nodata=layer["nodata"], dst_transform=destination_transform, dst_crs="EPSG:3857",
                      dst_nodata=layer["nodata"], resampling=resampling)
            indexed = destination.astype(np.uint8) if layer["categorical"] else quantise(destination, layer["range"], steps)
            sizes += write_tiles(output_directory / name, zoom, first_column, first_row, indexed, layer["palette"])
            resampling_by_zoom[zoom] = {"method": resampling.name, "ground_metres_per_pixel": round(ground_resolution, 1)}
        report[name] = {"tiles": len(sizes), "bytes": sum(sizes), "largest_tile_bytes": max(sizes),
                        "resampling_by_zoom": resampling_by_zoom}
        print(f"{name}: {len(sizes)} tiles, {sum(sizes) / 1e6:.2f} MB", flush=True)
    manifest = read_manifest()
    acquisitions = manifest["composite"]["acquisition_ids"]
    stored_dates = sorted(entry["datetime"][:10] for entry in manifest["acquire"]["acquisitions"] if entry["stored"])
    metadata = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "Sentinel-2 index analysis (this project)",
        "source": {
            "product": "Sentinel-2 Level-2A surface reflectance, Collection 1",
            "provider": "ESA Copernicus, distributed by Element 84 Earth Search on AWS",
            "stac_collection": f"{config['imagery']['stac_api']}/collections/{config['imagery']['collection']}",
            "attribution": "Contains modified Copernicus Sentinel data 2025",
            "processing_baseline": ", ".join(manifest["plan"]["processing_baselines"]),
        },
        "period": {"start": config["imagery"]["start"][:10], "end": config["imagery"]["end"][:10],
                   "first_acquisition": stored_dates[0], "last_acquisition": stored_dates[-1]},
        "acquisitions_used": len(acquisitions),
        "composite": "Median of per-observation index values",
        "resolution_m": config["grid"]["resolution"],
        "grid_crs": config["grid"]["crs"],
        "minimum_valid_observations": config["composite"]["minimum_valid_observations"],
        "tile_size": web["tile_size"],
        "min_zoom": web["min_zoom"],
        "max_zoom": web["max_zoom"],
        "bounds": [west, south, east, north],
        "layers": [
            {"id": "classes", "kind": "categorical", "title": "Index rule classes", "path": "classes/{z}/{x}/{y}.png",
             "classes": web["classes"]},
            *[{"id": name, "kind": "continuous", "title": web["indices"][name]["title"],
               "formula": web["indices"][name]["formula"], "path": f"{name}/{{z}}/{{x}}/{{y}}.png",
               "range": web["indices"][name]["range"], "stops": web["indices"][name]["stops"],
               "steps": steps} for name in index_names],
        ],
    }
    write_json(output_directory / "layers.json", metadata)
    total_bytes = sum(entry["bytes"] for entry in report.values()) + (output_directory / "layers.json").stat().st_size
    details = {"output": web["output"], "zooms": [web["min_zoom"], web["max_zoom"]], "layers": report,
               "total_bytes": total_bytes, "total_files": sum(entry["tiles"] for entry in report.values()) + 1,
               "seconds": round(time.time() - started, 1)}
    update_manifest("export", details)
    print(f"total {total_bytes / 1e6:.2f} MB in {details['total_files']} files")
    return details

