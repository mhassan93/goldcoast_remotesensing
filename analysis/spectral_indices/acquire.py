import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MULTIRANGE", "YES")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "3")

import numpy as np
import rasterio
from rasterio.windows import Window

from .grid import boundary_mask, build_grid
from .manifest import update_manifest
from .settings import load_config, read_json, work_path, write_json
from .stac import group_acquisitions, search_bbox, search_items

cached_band_order = ("green", "red", "nir", "swir1", "scl")


def tile_layouts(items, quality_asset):
    layouts = {}
    for item in items:
        asset = item["assets"][quality_asset]
        scale_x, _, left, _, scale_y, top = asset["proj:transform"][:6]
        rows, columns = asset["proj:shape"]
        layouts.setdefault(
            item["properties"]["grid:code"],
            {"epsg": item["properties"]["proj:epsg"], "left": left, "top": top,
             "right": left + columns * scale_x, "bottom": top + rows * scale_y},
        )
    return layouts


def assign_grid_rows(layouts, grid):
    for code, layout in layouts.items():
        if f"EPSG:{layout['epsg']}" != grid.crs:
            raise ValueError(f"Tile {code} is in EPSG:{layout['epsg']}, not the grid CRS {grid.crs}")
        if layout["left"] > grid.left or layout["right"] < grid.right:
            raise ValueError(f"Tile {code} does not span the full grid width")
    ordered = sorted(layouts.items(), key=lambda entry: -entry[1]["top"])
    parts = []
    row_start = 0
    for position, (code, layout) in enumerate(ordered):
        if position + 1 < len(ordered):
            next_top = ordered[position + 1][1]["top"]
            split_y = (layout["bottom"] + next_top) / 2
            row_end = round((grid.top - split_y) / grid.resolution)
        else:
            row_end = grid.height
        row_end = max(row_start, min(grid.height, row_end))
        if layout["top"] < grid.top - row_start * grid.resolution or layout["bottom"] > grid.top - row_end * grid.resolution:
            raise ValueError(f"Tile {code} does not cover grid rows {row_start}-{row_end}")
        if row_end > row_start:
            parts.append({"tile": code, "row_start": row_start, "row_end": row_end})
        row_start = row_end
    if row_start != grid.height:
        raise ValueError("The MGRS tiles do not cover every grid row")
    return parts


def asset_keys(config):
    bands = config["imagery"]["bands"]
    return {"green": bands["green"], "red": bands["red"], "nir": bands["nir"], "swir1": bands["swir1"],
            "scl": config["imagery"]["quality_asset"]}


def plan(config=None):
    config = config or load_config()
    started = time.time()
    grid, _, transformer = build_grid(config)
    items = search_items(config)
    acquisitions = group_acquisitions(items)
    layouts = tile_layouts(items, config["imagery"]["quality_asset"])
    parts = assign_grid_rows(layouts, grid)
    keys = asset_keys(config)
    tile_area = {code: (layout["right"] - layout["left"]) * (layout["top"] - layout["bottom"]) for code, layout in layouts.items()}
    part_area = {part["tile"]: (part["row_end"] - part["row_start"]) * grid.width * grid.resolution ** 2 for part in parts}
    full_tile_bytes = 0
    windowed_estimate = 0
    for item in items:
        code = item["properties"]["grid:code"]
        for name, key in keys.items():
            asset = item["assets"][key]
            full_tile_bytes += asset["file:size"]
            fraction = part_area.get(code, 0) / tile_area[code]
            overview_factor = 0.25 if asset["gsd"] < grid.resolution else 1.0
            windowed_estimate += asset["file:size"] * fraction * overview_factor
    plan_details = {
        "stac_api": config["imagery"]["stac_api"],
        "collection": config["imagery"]["collection"],
        "search_bbox_lonlat": search_bbox(config),
        "datetime_range": [config["imagery"]["start"], config["imagery"]["end"]],
        "item_count": len(items),
        "acquisition_count": len(acquisitions),
        "tiles": layouts,
        "grid": grid.describe(),
        "grid_parts": parts,
        "boundary_transformation": {"source": config["study_area"]["boundary_crs"], "target": config["grid"]["crs"],
                                    "operation": transformer.get_last_used_operation().description,
                                    "stated_accuracy_m": transformer.get_last_used_operation().accuracy},
        "assets": keys,
        "processing_baselines": sorted({acquisition["processing_baseline"] for acquisition in acquisitions}),
        "platforms": sorted({acquisition["platform"] for acquisition in acquisitions}),
        "relative_orbits": sorted({acquisition["relative_orbit"] for acquisition in acquisitions}),
        "full_tile_bytes_for_needed_assets": full_tile_bytes,
        "windowed_read_estimate_bytes": round(windowed_estimate),
        "seconds": round(time.time() - started, 1),
    }
    write_json(work_path("stac_items.json"), items)
    write_json(work_path("plan.json"), {**plan_details, "acquisitions": [
        {key: value for key, value in acquisition.items() if key != "items"} | {"item_ids": [item["id"] for item in acquisition["items"]]}
        for acquisition in acquisitions]})
    update_manifest("plan", plan_details)
    print(f"{len(items)} items, {len(acquisitions)} acquisitions, tiles {sorted(layouts)}")
    print(f"grid {grid.width} x {grid.height} at {grid.resolution} m, parts {parts}")
    print(f"needed assets as whole files: {full_tile_bytes / 1e9:.2f} GB; windowed estimate: {windowed_estimate / 1e9:.2f} GB")
    return plan_details


def window_bytes(dataset, window):
    block_height, block_width = dataset.block_shapes[0]
    first_column, last_column = int(window.col_off) // block_width, (int(window.col_off + window.width) - 1) // block_width
    first_row, last_row = int(window.row_off) // block_height, (int(window.row_off + window.height) - 1) // block_height
    total = 0
    for block_row in range(first_row, last_row + 1):
        for block_column in range(first_column, last_column + 1):
            size = dataset.get_tag_item(f"BLOCK_SIZE_{block_column}_{block_row}", "TIFF", bidx=1)
            if size is None:
                return None
            total += int(size)
    return total


def read_part(href, grid, part, native_resolution):
    overview_level = 0 if native_resolution < grid.resolution else None
    with rasterio.open(href, overview_level=overview_level) as dataset:
        if abs(dataset.res[0] - grid.resolution) > 1e-6 or dataset.crs.to_string() != grid.crs:
            raise ValueError(f"{href} does not match the grid ({dataset.res}, {dataset.crs})")
        column_offset = (grid.left - dataset.transform.c) / grid.resolution
        row_offset = (dataset.transform.f - (grid.top - part["row_start"] * grid.resolution)) / grid.resolution
        if abs(column_offset - round(column_offset)) > 1e-6 or abs(row_offset - round(row_offset)) > 1e-6:
            raise ValueError(f"{href} is not aligned to the analysis grid")
        window = Window(round(column_offset), round(row_offset), grid.width, part["row_end"] - part["row_start"])
        return dataset.read(1, window=window), window_bytes(dataset, window)


def band_scaling(items, keys):
    scaling = {}
    for name, key in keys.items():
        if name == "scl":
            continue
        values = {(band.get("scale", 1.0), band.get("offset", 0.0))
                  for item in items for band in item["assets"][key]["raster:bands"]}
        if len(values) != 1:
            raise ValueError(f"Items in one acquisition disagree on scale and offset for {name}: {values}")
        scale, offset = values.pop()
        scaling[name] = {"scale": scale, "offset": offset}
    return scaling


def acquire_one(acquisition, grid, parts, mask, config):
    status_path = work_path("acquisitions", f"{acquisition['id']}.json")
    cache_path = work_path("acquisitions", f"{acquisition['id']}.tif")
    if status_path.exists():
        return read_json(status_path)
    started = time.time()
    keys = asset_keys(config)
    items_by_tile = {item["properties"]["grid:code"]: item for item in acquisition["items"]}
    bytes_read = {}
    stack = np.zeros((len(cached_band_order), grid.height, grid.width), dtype=np.uint16)

    def read_band(name):
        total = 0
        for part in parts:
            item = items_by_tile.get(part["tile"])
            if item is None:
                continue
            asset = item["assets"][keys[name]]
            data, size = read_part(asset["href"], grid, part, asset["gsd"])
            stack[cached_band_order.index(name), part["row_start"]:part["row_end"]] = data
            total = None if total is None or size is None else total + size
        bytes_read[name] = total

    read_band("scl")
    scene_classes = stack[cached_band_order.index("scl")]
    clear_fraction = float((np.isin(scene_classes, config["masks"]["clear_scene_classes"]) & mask).sum() / mask.sum())
    status = {
        "id": acquisition["id"],
        "datatake_id": acquisition["datatake_id"],
        "datetime": acquisition["datetime"],
        "platform": acquisition["platform"],
        "relative_orbit": acquisition["relative_orbit"],
        "processing_baseline": acquisition["processing_baseline"],
        "item_ids": [item["id"] for item in acquisition["items"]],
        "tiles_used": [part["tile"] for part in parts if part["tile"] in items_by_tile],
        "clear_fraction_in_boundary": round(clear_fraction, 5),
        "stored": clear_fraction >= config["imagery"]["minimum_clear_fraction"],
    }
    if status["stored"]:
        for name in ("green", "red", "nir", "swir1"):
            read_band(name)
        status["scaling"] = band_scaling(acquisition["items"], keys)
        profile = {
            "driver": "GTiff", "width": grid.width, "height": grid.height, "count": len(cached_band_order),
            "dtype": "uint16", "crs": grid.crs, "transform": grid.transform, "nodata": 0,
            "compress": "deflate", "predictor": 2, "tiled": False, "blockysize": config["composite"]["block_rows"],
        }
        with rasterio.open(cache_path, "w", **profile) as cache:
            cache.write(stack)
            cache.descriptions = cached_band_order
        status["cache_bytes"] = cache_path.stat().st_size
    status["bytes_read"] = bytes_read
    status["seconds"] = round(time.time() - started, 1)
    write_json(status_path, status)
    return status


def acquire(config=None):
    config = config or load_config()
    started = time.time()
    grid, boundary, _ = build_grid(config)
    mask = boundary_mask(grid, boundary)
    plan_record = read_json(work_path("plan.json"))
    items = {item["id"]: item for item in read_json(work_path("stac_items.json"))}
    acquisitions = [{**acquisition, "items": [items[item_id] for item_id in acquisition["item_ids"]]}
                    for acquisition in plan_record["acquisitions"]]
    parts = plan_record["grid_parts"]
    statuses = []
    with ThreadPoolExecutor(max_workers=config["imagery"]["parallel_acquisitions"]) as executor:
        futures = {executor.submit(acquire_one, acquisition, grid, parts, mask, config): acquisition for acquisition in acquisitions}
        for done, future in enumerate(as_completed(futures), start=1):
            status = future.result()
            statuses.append(status)
            read_total = sum(value or 0 for value in status["bytes_read"].values())
            print(f"[{done}/{len(acquisitions)}] {status['id']} clear {status['clear_fraction_in_boundary']:.3f} "
                  f"{'stored' if status['stored'] else 'skipped'} {read_total / 1e6:.1f} MB {status['seconds']} s", flush=True)
    statuses.sort(key=lambda status: status["datetime"])
    stored = [status for status in statuses if status["stored"]]
    total_bytes = sum(value or 0 for status in statuses for value in status["bytes_read"].values())
    unknown = sum(1 for status in statuses for value in status["bytes_read"].values() if value is None)
    details = {
        "acquisitions_considered": len(statuses),
        "acquisitions_stored": len(stored),
        "acquisitions_skipped_below_clear_fraction": len(statuses) - len(stored),
        "minimum_clear_fraction": config["imagery"]["minimum_clear_fraction"],
        "compressed_bytes_read": total_bytes,
        "reads_with_unknown_size": unknown,
        "cache_bytes": sum(status.get("cache_bytes", 0) for status in stored),
        "seconds_this_run": round(time.time() - started, 1),
        "sum_of_acquisition_seconds": round(sum(status["seconds"] for status in statuses), 1),
        "parallel_acquisitions": config["imagery"]["parallel_acquisitions"],
        "acquisitions": [{key: status[key] for key in ("id", "datetime", "platform", "relative_orbit", "item_ids",
                                                      "tiles_used", "clear_fraction_in_boundary", "stored")}
                         for status in statuses],
    }
    update_manifest("acquire", details)
    print(f"stored {len(stored)} of {len(statuses)} acquisitions; read {total_bytes / 1e9:.2f} GB")
    return details
