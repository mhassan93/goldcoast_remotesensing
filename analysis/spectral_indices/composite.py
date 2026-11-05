import time

import numpy as np
import rasterio
from rasterio.windows import Window

from .acquire import cached_band_order
from .grid import boundary_mask, build_grid
from .manifest import update_manifest
from .settings import load_config, read_json, work_path, work_root

index_names = ("ndvi", "ndbi", "mndwi")
count_names = ("clear", "ndvi", "ndbi", "mndwi")


def stored_acquisitions():
    statuses = [read_json(path) for path in sorted((work_root / "acquisitions").glob("*.json"))]
    return sorted((status for status in statuses if status["stored"]), key=lambda status: status["datetime"])


def dilate(mask, radius):
    if radius == 0:
        return mask
    grown = mask.copy()
    for shift in range(1, radius + 1):
        grown[..., shift:, :] |= mask[..., :-shift, :]
        grown[..., :-shift, :] |= mask[..., shift:, :]
    rows_grown = grown.copy()
    for shift in range(1, radius + 1):
        grown[..., :, shift:] |= rows_grown[..., :, :-shift]
        grown[..., :, :-shift] |= rows_grown[..., :, shift:]
    return grown


def median_ignoring_nan(values):
    valid_count = np.count_nonzero(~np.isnan(values), axis=0)
    ordered = np.sort(values, axis=0)
    lower_position = np.clip((valid_count - 1) // 2, 0, None)
    upper_position = np.clip(valid_count // 2, 0, None)
    lower = np.take_along_axis(ordered, lower_position[None], axis=0)[0]
    upper = np.take_along_axis(ordered, upper_position[None], axis=0)[0]
    median = (lower + upper) / 2
    median[valid_count == 0] = np.nan
    return median.astype(np.float32), valid_count


def normalised_difference(first, second, usable, minimum_denominator):
    denominator = first + second
    usable = usable & (denominator > minimum_denominator)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.where(usable, (first - second) / denominator, np.nan).astype(np.float32)
    return values


def composite(config=None):
    config = config or load_config()
    started = time.time()
    grid, boundary, _ = build_grid(config)
    inside = boundary_mask(grid, boundary)
    acquisitions = stored_acquisitions()
    if not acquisitions:
        raise SystemExit("No stored acquisitions. Run the acquire stage first.")
    masks = config["masks"]
    limits = config["indices"]
    formulas = config["indices"]["formulas"]
    radius = masks["buffer_pixels"]
    block_rows = config["composite"]["block_rows"]
    medians = np.full((len(index_names), grid.height, grid.width), np.nan, dtype=np.float32)
    counts = np.zeros((len(count_names), grid.height, grid.width), dtype=np.uint16)
    scales = {name: np.array([status["scaling"][name]["scale"] for status in acquisitions], dtype=np.float32)[:, None, None]
              for name in ("green", "red", "nir", "swir1")}
    offsets = {name: np.array([status["scaling"][name]["offset"] for status in acquisitions], dtype=np.float32)[:, None, None]
               for name in ("green", "red", "nir", "swir1")}
    datasets = [rasterio.open(work_path("acquisitions", f"{status['id']}.tif")) for status in acquisitions]
    try:
        for row_start in range(0, grid.height, block_rows):
            row_end = min(grid.height, row_start + block_rows)
            read_start, read_end = max(0, row_start - radius), min(grid.height, row_end + radius)
            window = Window(0, read_start, grid.width, read_end - read_start)
            stack = np.stack([dataset.read(window=window) for dataset in datasets])
            crop = slice(row_start - read_start, row_start - read_start + (row_end - row_start))
            scene_classes = stack[:, cached_band_order.index("scl")]
            hazard = dilate(np.isin(scene_classes, masks["buffered_scene_classes"]), radius)
            clear = np.isin(scene_classes, masks["clear_scene_classes"]) & ~hazard
            clear = clear[:, crop] & inside[row_start:row_end][None]
            reflectance = {}
            band_usable = {}
            for name in ("green", "red", "nir", "swir1"):
                digital_numbers = stack[:, cached_band_order.index(name), crop]
                values = digital_numbers.astype(np.float32) * scales[name] + offsets[name]
                reflectance[name] = values
                band_usable[name] = ((digital_numbers > 0) & (values > limits["minimum_reflectance"])
                                     & (values <= limits["maximum_reflectance"]))
            counts[0, row_start:row_end] = clear.sum(axis=0)
            for position, index_name in enumerate(index_names):
                first, second = formulas[index_name]
                usable = clear & band_usable[first] & band_usable[second]
                values = normalised_difference(reflectance[first], reflectance[second], usable, limits["minimum_denominator"])
                medians[position, row_start:row_end], counts[position + 1, row_start:row_end] = median_ignoring_nan(values)
            print(f"rows {row_start}-{row_end} of {grid.height}", flush=True) if row_start % (block_rows * 10) == 0 else None
    finally:
        for dataset in datasets:
            dataset.close()
    medians[:, ~inside] = np.nan
    counts[:, ~inside] = 0
    profile = {"driver": "GTiff", "width": grid.width, "height": grid.height, "crs": grid.crs,
               "transform": grid.transform, "compress": "deflate", "tiled": True, "blockxsize": 256, "blockysize": 256}
    with rasterio.open(work_path("composite", "index_medians.tif"), "w", count=3, dtype="float32", nodata=np.nan,
                       predictor=3, **profile) as output:
        output.write(medians)
        output.descriptions = index_names
    with rasterio.open(work_path("composite", "observation_counts.tif"), "w", count=4, dtype="uint16", nodata=0,
                       predictor=2, **profile) as output:
        output.write(counts)
        output.descriptions = count_names
    with rasterio.open(work_path("composite", "boundary_mask.tif"), "w", count=1, dtype="uint8", nodata=0,
                       predictor=2, **profile) as output:
        output.write(inside.astype(np.uint8)[None])
    inside_counts = counts[:, inside]
    minimum = config["composite"]["minimum_valid_observations"]
    details = {
        "method": config["composite"]["method"],
        "indices_calculated": "per observation, before compositing",
        "period": [config["imagery"]["start"], config["imagery"]["end"]],
        "acquisitions_used": len(acquisitions),
        "acquisition_ids": [status["id"] for status in acquisitions],
        "masks": masks,
        "index_limits": {key: value for key, value in limits.items() if key != "formulas"},
        "formulas": formulas,
        "pixels_inside_boundary": int(inside.sum()),
        "observation_count_percentiles_inside": {
            name: {str(p): float(np.percentile(inside_counts[position], p)) for p in (0, 1, 5, 25, 50, 75, 95, 100)}
            for position, name in enumerate(count_names)},
        "pixels_below_minimum_observations": {name: int((inside_counts[position] < minimum).sum())
                                              for position, name in enumerate(count_names)},
        "minimum_valid_observations": minimum,
        "outputs": ["work/composite/index_medians.tif", "work/composite/observation_counts.tif",
                    "work/composite/boundary_mask.tif"],
        "seconds": round(time.time() - started, 1),
    }
    update_manifest("composite", details)
    print(f"composited {len(acquisitions)} acquisitions in {details['seconds']} s")
    print(details["observation_count_percentiles_inside"])
    return details
