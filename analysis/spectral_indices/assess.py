import csv
import math
import os
from collections import Counter, defaultdict

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

import numpy as np
import rasterio
from pyproj import Transformer

from .classify import rule_limits
from .composite import count_names, index_names
from .grid import build_grid
from .manifest import update_manifest
from .samples import cell_centre_lonlat, grid_cell, read_samples
from .settings import load_config, results_path, work_path, write_json

dea_level3_names = {111: "Cultivated Terrestrial Vegetation", 112: "(Semi-)Natural Terrestrial Vegetation",
                    124: "Natural Aquatic Vegetation", 215: "Artificial Surface", 216: "Natural Bare Surface",
                    220: "Water", 255: "No data"}
dea_groups = {111: "vegetation", 112: "vegetation", 124: "vegetation", 215: "artificial", 216: "bare_or_sand",
              220: "water", 255: "no_data"}
rule_groups = {"vegetation": "vegetation", "water": "water", "candidate_artificial": "artificial",
               "uncertain_other": "uncertain_or_other", "insufficient_observations": "insufficient", "no_data": "no_data"}
expected_rule_group = {"vegetation": "vegetation", "water": "water", "artificial": "artificial",
                       "bare_or_sand": "uncertain_or_other"}
scored_labels = set(expected_rule_group)
scored_confidence = {"high", "medium"}


def wilson_interval(successes, total, z=1.96):
    if total == 0:
        return None, None
    proportion = successes / total
    centre = (proportion + z * z / (2 * total)) / (1 + z * z / total)
    half_width = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return round(centre - half_width, 3), round(centre + half_width, 3)


def dea_values(config, samples):
    to_albers = Transformer.from_crs("EPSG:4326", "EPSG:3577", always_xy=True)
    values = {}
    for year in config["assessment"]["dea_years"]:
        url = "/vsicurl/" + config["assessment"]["dea_level3_mosaic"].format(year=year)
        with rasterio.open(url) as mosaic:
            points = [to_albers.transform(sample["cell_lon"], sample["cell_lat"]) for sample in samples]
            values[year] = [int(value[0]) for value in mosaic.sample(points)]
    return values


def sample_rasters(config):
    grid, _, _ = build_grid(config)
    samples = read_samples(config)
    with rasterio.open(work_path("composite", "index_medians.tif")) as source:
        medians = source.read()
    with rasterio.open(work_path("composite", "observation_counts.tif")) as source:
        counts = source.read()
    with rasterio.open(work_path("classification", "index_rule_classes.tif")) as source:
        classes = source.read(1)
    class_names = {value: name for name, value in config["classification"]["classes"].items()}
    rows = []
    for sample in samples:
        row, column, cell = grid_cell(sample, grid)
        cell_lon, cell_lat = cell_centre_lonlat(cell, grid)
        record = {**sample, "cell_lon": round(cell_lon, 6), "cell_lat": round(cell_lat, 6), "grid_row": row,
                  "grid_column": column}
        for position, name in enumerate(index_names):
            value = float(medians[position, row, column])
            record[name] = round(value, 3) if np.isfinite(value) else ""
        for position, name in enumerate(count_names):
            record[f"{name}_observations"] = int(counts[position, row, column])
        record["rule_class"] = class_names[int(classes[row, column])]
        rows.append(record)
    for year, values in dea_values(config, rows).items():
        for record, value in zip(rows, values):
            record[f"dea_{year}_value"] = value
            record[f"dea_{year}_class"] = dea_level3_names.get(value, str(value))
    return rows


def write_table(rows, path):
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def calibrate(config=None):
    config = config or load_config()
    rows = [row for row in sample_rasters(config) if row["set"] == "calibration"]
    write_table(rows, results_path("calibration_samples.csv"))
    summary = []
    by_label = defaultdict(list)
    for row in rows:
        if row["reference_label"]:
            by_label[row["reference_label"]].append(row)
    for label, members in sorted(by_label.items()):
        entry = {"reference_label": label, "samples": len(members)}
        for name in index_names:
            values = [member[name] for member in members if member[name] != ""]
            entry[f"{name}_min"] = min(values) if values else ""
            entry[f"{name}_median"] = round(float(np.median(values)), 3) if values else ""
            entry[f"{name}_max"] = max(values) if values else ""
        summary.append(entry)
    write_table(summary, results_path("calibration_summary.csv"))
    update_manifest("calibrate", {"calibration_samples": len(rows), "summary": summary,
                                  "outputs": ["analysis/results/calibration_samples.csv",
                                              "analysis/results/calibration_summary.csv"]})
    for entry in summary:
        print(entry)
    return summary


def agreement(rows, predicted, expected):
    scored = [row for row in rows if predicted(row) is not None and expected(row) is not None]
    matches = sum(1 for row in scored if predicted(row) == expected(row))
    low, high = wilson_interval(matches, len(scored))
    return {"samples": len(scored), "agreeing": matches,
            "proportion": round(matches / len(scored), 3) if scored else None, "wilson_95": [low, high]}


def assess(config=None):
    config = config or load_config()
    rows = sample_rasters(config)
    reference_dates = {}
    dates_path = results_path("reference_imagery_dates.csv")
    if dates_path.exists():
        with dates_path.open(encoding="utf-8") as dates_file:
            reference_dates = {row["sample_id"]: row for row in csv.DictReader(dates_file)}
    for row in rows:
        dates = reference_dates.get(row["sample_id"], {})
        row["reference_imagery_date"] = dates.get("recent_imagery_date", "")
        row["earlier_imagery_dates"] = dates.get("earlier_imagery_dates", "")
        row["rule_group"] = rule_groups[row["rule_class"]]
        row["dea_2025_group"] = dea_groups.get(row["dea_2025_value"], "other")
        row["inside_study_area"] = "yes" if row["rule_class"] != "no_data" else "no"
        scorable = (row["reference_label"] in scored_labels and row["reference_confidence"] in scored_confidence
                    and row["inside_study_area"] == "yes")
        row["scored"] = "yes" if scorable else "no"
        row["rule_matches_reference"] = (
            ("yes" if row["rule_group"] == expected_rule_group[row["reference_label"]] else "no") if scorable else "")
        row["dea_2025_matches_reference"] = (
            ("yes" if row["dea_2025_group"] == row["reference_label"] else "no") if scorable else "")
        row["rule_agrees_with_dea_2025"] = "yes" if (
            row["rule_group"] == row["dea_2025_group"]
            or (row["rule_group"] == "uncertain_or_other" and row["dea_2025_group"] == "bare_or_sand")) else "no"
    write_table(rows, results_path("sample_assessment.csv"))
    assessment_rows = [row for row in rows if row["set"] == "assessment"]
    scored_rows = [row for row in assessment_rows if row["scored"] == "yes"]
    rule_vs_reference = agreement(scored_rows, lambda row: row["rule_group"],
                                  lambda row: expected_rule_group[row["reference_label"]])
    dea_vs_reference = agreement(scored_rows, lambda row: row["dea_2025_group"], lambda row: row["reference_label"])
    artificial_rows = [row for row in scored_rows if row["reference_label"] == "artificial"]
    confusion = Counter((row["reference_label"], row["rule_group"]) for row in scored_rows)
    dea_confusion = Counter((row["reference_label"], row["dea_2025_group"]) for row in scored_rows)
    summary = {
        "reference": "Visual interpretation of dated Esri World Imagery (Vantor) chips, cross-checked against "
                     "Queensland Government 2022 aerial imagery; one interpreter, not field-verified.",
        "scored_definition": "Assessment-set samples inside the study boundary whose reference label is vegetation, "
                             "water, artificial or bare_or_sand with high or medium confidence. Mixed, low-confidence "
                             "and outside-boundary samples are listed but not scored.",
        "assessment_samples": len(assessment_rows),
        "scored_samples": len(scored_rows),
        "rule_vs_reference": rule_vs_reference,
        "dea_2025_vs_reference": dea_vs_reference,
        "reference_artificial_detected": {
            "samples": len(artificial_rows),
            "rule_candidate_artificial": sum(1 for row in artificial_rows if row["rule_group"] == "artificial"),
            "dea_2025_artificial_surface": sum(1 for row in artificial_rows if row["dea_2025_group"] == "artificial"),
        },
        "samples_outside_study_area": [row["sample_id"] for row in rows if row["inside_study_area"] == "no"],
        "rule_agrees_with_dea_2025_inside_study_area": agreement(
            [row for row in rows if row["inside_study_area"] == "yes"],
            lambda row: row["rule_agrees_with_dea_2025"], lambda row: "yes"),
        "rule_confusion": {f"{reference} -> {predicted}": count for (reference, predicted), count in sorted(confusion.items())},
        "dea_2025_confusion": {f"{reference} -> {predicted}": count
                               for (reference, predicted), count in sorted(dea_confusion.items())},
        "rule_limits": rule_limits(config["classification"]),
        "outputs": ["analysis/results/sample_assessment.csv", "analysis/results/assessment_summary.json"],
    }
    write_json(results_path("assessment_summary.json"), summary)
    update_manifest("assess", summary)
    for key in ("rule_vs_reference", "dea_2025_vs_reference", "reference_artificial_detected",
                "rule_agrees_with_dea_2025_inside_study_area"):
        print(key, summary[key])
    return summary

