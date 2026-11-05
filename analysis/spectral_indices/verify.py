import math
import statistics

import numpy as np
import rasterio
from rasterio.windows import Window

from .acquire import asset_keys, cached_band_order, read_part
from .classify import rule_limits
from .composite import count_names, index_names, stored_acquisitions
from .grid import boundary_mask, build_grid, polygons_of
from .manifest import update_manifest
from .samples import grid_cell, read_samples
from .settings import load_config, read_json, results_path, work_path, write_json


def ring_area(ring):
    return 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1])))


def polygon_area(geometry):
    return sum(ring_area(polygon[0]) - sum(ring_area(hole) for hole in polygon[1:]) for polygon in polygons_of(geometry))


def scalar_index(first, second, limits):
    if first is None or second is None:
        return None
    if not (limits["minimum_reflectance"] < first <= limits["maximum_reflectance"]):
        return None
    if not (limits["minimum_reflectance"] < second <= limits["maximum_reflectance"]):
        return None
    if first + second <= limits["minimum_denominator"]:
        return None
    return (first - second) / (first + second)


def scalar_class(ndvi, ndbi, mndwi, enough, config):
    limits = rule_limits(config["classification"])
    if not enough:
        return "insufficient_observations"
    if mndwi >= limits["water_at_least"]:
        return "water"
    if ndvi >= limits["vegetation_at_least"]:
        return "vegetation"
    in_bare_or_sand_range = limits["bare_or_sand_ndbi_from"] <= ndbi < limits["bare_or_sand_ndbi_below"]
    if (ndbi >= limits["artificial_ndbi_at_least"] and not in_bare_or_sand_range
            and ndvi <= limits["not_vegetation_at_most"] and mndwi <= limits["not_water_at_most"]):
        return "candidate_artificial"
    return "uncertain_other"


def pixel_observations(acquisitions, row, column, config):
    masks = config["masks"]
    radius = masks["buffer_pixels"]
    observations = []
    for status in acquisitions:
        with rasterio.open(work_path("acquisitions", f"{status['id']}.tif")) as cache:
            window = Window(column - radius, row - radius, 2 * radius + 1, 2 * radius + 1)
            block = cache.read(window=window, boundless=True, fill_value=0)
        scene_classes = block[cached_band_order.index("scl")]
        if int(scene_classes[radius, radius]) not in masks["clear_scene_classes"]:
            continue
        if any(int(value) in masks["buffered_scene_classes"] for value in scene_classes.ravel()):
            continue
        reflectance = {}
        for name in ("green", "red", "nir", "swir1"):
            digital_number = int(block[cached_band_order.index(name), radius, radius])
            scaling = status["scaling"][name]
            reflectance[name] = digital_number * scaling["scale"] + scaling["offset"] if digital_number > 0 else None
        observations.append(reflectance)
    return observations


def verify(config=None):
    config = config or load_config()
    report = {}
    grid, boundary, _ = build_grid(config)
    inside = boundary_mask(grid, boundary)
    report["grid_alignment"] = {
        "origin_multiple_of_resolution": grid.left % grid.resolution == 0 and grid.top % grid.resolution == 0,
        "grid": grid.describe(),
    }
    boundary_area_km2 = polygon_area(boundary) / 1e6
    mask_area_km2 = inside.sum() * grid.resolution ** 2 / 1e6
    report["boundary_mask"] = {
        "polygon_area_in_grid_crs_km2": round(boundary_area_km2, 2),
        "masked_pixel_area_km2": round(float(mask_area_km2), 2),
        "relative_difference": round(float(abs(mask_area_km2 - boundary_area_km2) / boundary_area_km2), 5),
    }
    acquisitions = stored_acquisitions()
    plan_record = read_json(work_path("plan.json"))
    keys = asset_keys(config)
    first = acquisitions[len(acquisitions) // 2]
    items = {item["id"]: item for item in read_json(work_path("stac_items.json"))}
    part = plan_record["grid_parts"][0]
    item = next(items[item_id] for item_id in first["item_ids"] if items[item_id]["properties"]["grid:code"] == part["tile"])
    test_row = part["row_start"] + (part["row_end"] - part["row_start"]) // 2
    test_column = grid.width // 2
    alignment_checks = {}
    for name in ("red", "nir"):
        asset = item["assets"][keys[name]]
        single_row_part = {"row_start": test_row, "row_end": test_row + 1}
        direct, _ = read_part(asset["href"], grid, single_row_part, asset["gsd"])
        with rasterio.open(work_path("acquisitions", f"{first['id']}.tif")) as cache:
            cached = cache.read(cached_band_order.index(name) + 1, window=Window(0, test_row, grid.width, 1))
        alignment_checks[name] = {"acquisition": first["id"], "row": test_row,
                                  "identical_row_values": bool(np.array_equal(direct, cached)),
                                  "example": [int(direct[0, test_column]), int(cached[0, test_column])]}
    report["grid_alignment"]["cache_matches_source_cog"] = alignment_checks
    with rasterio.open(work_path("composite", "index_medians.tif")) as source:
        medians = source.read()
    with rasterio.open(work_path("composite", "observation_counts.tif")) as source:
        counts = source.read()
    with rasterio.open(work_path("classification", "index_rule_classes.tif")) as source:
        classes = source.read(1)
    finite = np.isfinite(medians)
    minimum = config["composite"]["minimum_valid_observations"]
    class_values = config["classification"]["classes"]
    report["valid_data"] = {
        "all_finite_values_within_minus_one_to_one": bool(np.all(np.abs(medians[finite]) <= 1)),
        "no_values_outside_boundary": bool(not finite[:, ~inside].any() and not counts[:, ~inside].any()),
        "nan_exactly_where_index_count_is_zero": bool(all(
            np.array_equal(~finite[position], counts[count_names.index(name)] == 0)
            for position, name in enumerate(index_names))),
        "index_counts_never_exceed_clear_count": bool(np.all(counts[1:] <= counts[0])),
        "outside_boundary_is_class_no_data": bool(np.all(classes[~inside] == class_values["no_data"])),
        "low_count_pixels_are_insufficient": bool(np.all(
            classes[inside & (counts[1:].min(axis=0) < minimum)] == class_values["insufficient_observations"])),
    }
    names = {value: name for name, value in class_values.items()}
    sample_checks = []
    limits = config["indices"]
    for sample in read_samples(config)[::6]:
        row, column, _ = grid_cell(sample, grid)
        observations = pixel_observations(acquisitions, row, column, config) if inside[row, column] else []
        recomputed = {}
        for name, (first_band, second_band) in config["indices"]["formulas"].items():
            values = [scalar_index(observation[first_band], observation[second_band], limits) for observation in observations]
            values = [value for value in values if value is not None]
            recomputed[name] = (statistics.median(values) if values else math.nan, len(values))
        enough = all(count >= minimum for _, count in recomputed.values())
        expected_class = (scalar_class(recomputed["ndvi"][0], recomputed["ndbi"][0], recomputed["mndwi"][0], enough, config)
                          if inside[row, column] else "no_data")
        sample_checks.append({
            "sample_id": sample["sample_id"],
            "clear_observations": {"independent": len(observations), "pipeline": int(counts[0, row, column])},
            **{name: {"independent_median": round(value, 5) if not math.isnan(value) else None,
                      "pipeline_median": round(float(medians[index_names.index(name), row, column]), 5)
                      if np.isfinite(medians[index_names.index(name), row, column]) else None,
                      "independent_count": count, "pipeline_count": int(counts[count_names.index(name), row, column])}
               for name, (value, count) in recomputed.items()},
            "independent_class": expected_class,
            "pipeline_class": names[int(classes[row, column])],
        })
    report["sample_recomputation"] = sample_checks
    report["sample_recomputation_all_match"] = all(
        check["clear_observations"]["independent"] == check["clear_observations"]["pipeline"]
        and check["independent_class"] == check["pipeline_class"]
        and all(check[name]["independent_count"] == check[name]["pipeline_count"]
                and (check[name]["independent_median"] is None) == (check[name]["pipeline_median"] is None)
                and (check[name]["independent_median"] is None
                     or abs(check[name]["independent_median"] - check[name]["pipeline_median"]) < 1e-5)
                for name in index_names)
        for check in sample_checks)
    write_json(results_path("verification.json"), report)
    update_manifest("verify", {"output": "analysis/results/verification.json",
                               "boundary_mask": report["boundary_mask"], "valid_data": report["valid_data"],
                               "sample_recomputation_all_match": report["sample_recomputation_all_match"]})
    print({key: value for key, value in report.items() if key != "sample_recomputation"})
    return report
