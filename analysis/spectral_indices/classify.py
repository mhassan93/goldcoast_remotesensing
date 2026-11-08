import time

import numpy as np
import rasterio

from .composite import count_names, index_names
from .manifest import update_manifest
from .settings import load_config, work_path


def rule_limits(rules):
    return {
        "water_at_least": rules["water_mndwi"] + rules["water_margin"],
        "not_water_at_most": rules["water_mndwi"] - rules["water_margin"],
        "vegetation_at_least": rules["vegetation_ndvi"] + rules["vegetation_margin"],
        "not_vegetation_at_most": rules["vegetation_ndvi"] - rules["vegetation_margin"],
        "artificial_ndbi_at_least": rules["artificial_ndbi_minimum"],
        "bare_or_sand_ndbi_from": rules["bare_or_sand_ndbi_range"][0],
        "bare_or_sand_ndbi_below": rules["bare_or_sand_ndbi_range"][1],
    }


def in_bare_or_sand_range(ndbi, limits):
    return (ndbi >= limits["bare_or_sand_ndbi_from"]) & (ndbi < limits["bare_or_sand_ndbi_below"])


def classify_values(ndvi, ndbi, mndwi, enough_observations, inside, config):
    classes = config["classification"]["classes"]
    limits = rule_limits(config["classification"])
    result = np.full(ndvi.shape, classes["no_data"], dtype=np.uint8)
    assessable = inside & enough_observations
    water = assessable & (mndwi >= limits["water_at_least"])
    vegetation = assessable & ~water & (ndvi >= limits["vegetation_at_least"])
    artificial = (assessable & ~water & ~vegetation
                  & (ndbi >= limits["artificial_ndbi_at_least"])
                  & ~in_bare_or_sand_range(ndbi, limits)
                  & (ndvi <= limits["not_vegetation_at_most"])
                  & (mndwi <= limits["not_water_at_most"]))
    result[inside & ~enough_observations] = classes["insufficient_observations"]
    result[assessable] = classes["uncertain_other"]
    result[artificial] = classes["candidate_artificial"]
    result[vegetation] = classes["vegetation"]
    result[water] = classes["water"]
    return result


def classify(config=None):
    config = config or load_config()
    started = time.time()
    with rasterio.open(work_path("composite", "index_medians.tif")) as source:
        medians = source.read()
        profile = source.profile
    with rasterio.open(work_path("composite", "observation_counts.tif")) as source:
        counts = source.read()
    with rasterio.open(work_path("composite", "boundary_mask.tif")) as source:
        inside = source.read(1).astype(bool)
    minimum = config["composite"]["minimum_valid_observations"]
    enough = np.all([counts[count_names.index(name)] >= minimum for name in index_names], axis=0)
    enough &= np.all(np.isfinite(medians), axis=0)
    ndvi, ndbi, mndwi = (medians[index_names.index(name)] for name in ("ndvi", "ndbi", "mndwi"))
    classes = classify_values(ndvi, ndbi, mndwi, enough, inside, config)
    profile.update(count=1, dtype="uint8", nodata=config["classification"]["classes"]["no_data"], predictor=2)
    with rasterio.open(work_path("classification", "index_rule_classes.tif"), "w", **profile) as output:
        output.write(classes[None])
    names = {value: name for name, value in config["classification"]["classes"].items()}
    pixel_area_km2 = (config["grid"]["resolution"] ** 2) / 1e6
    class_counts = {names[value]: int((classes == value).sum()) for value in sorted(names)}
    details = {
        "rule_limits": rule_limits(config["classification"]),
        "thresholds": {key: value for key, value in config["classification"].items() if key != "classes"},
        "classes": config["classification"]["classes"],
        "precedence": [
            "no_data: outside the study boundary",
            "insufficient_observations: any index has fewer valid observations than the minimum",
            "water: MNDWI >= water_at_least",
            "vegetation: NDVI >= vegetation_at_least",
            "candidate_artificial: NDVI <= not_vegetation_at_most, MNDWI <= not_water_at_most, "
            "NDBI >= artificial_ndbi_at_least and NDBI outside the bare-or-sand range",
            "uncertain_other: every remaining assessable pixel",
        ],
        "pixel_counts": class_counts,
        "area_km2": {name: round(count * pixel_area_km2, 2) for name, count in class_counts.items()},
        "output": f"work/{config['year']}/classification/index_rule_classes.tif",
        "seconds": round(time.time() - started, 1),
    }
    update_manifest("classify", details)
    print(details["area_km2"])
    return details
