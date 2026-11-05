import csv
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw
from pyproj import Transformer

from .grid import build_grid
from .manifest import update_manifest
from .samples import grid_cell, read_samples
from .settings import load_config, results_path, work_path

chip_pixels = 320
chip_half_width_m = 120
user_agent = {"User-Agent": "goldcoast-remotesensing reference review"}


def fetch(url, parameters, attempts=4):
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(parameters)}", headers=user_agent)
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
            time.sleep(3 * (attempt + 1))


def imagery_date(service, x, y, extent):
    parameters = {"geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "sr": 3857, "layers": "top:0",
                  "tolerance": 0, "mapExtent": ",".join(str(value) for value in extent),
                  "imageDisplay": f"{chip_pixels},{chip_pixels},96", "returnGeometry": "false", "f": "json"}
    results = json.loads(fetch(f"{service}/identify", parameters)).get("results", [])
    attributes = results[0]["attributes"] if results else {}
    return attributes.get("DATE (YYYYMMDD)", ""), attributes.get("SOURCE_INFO", ""), attributes.get("RESOLUTION (M)", "")


def earlier_imagery_date(service, x, y):
    parameters = {"geometry": json.dumps({"x": x, "y": y, "spatialReference": {"wkid": 3857}}),
                  "geometryType": "esriGeometryPoint", "returnCatalogItems": "true", "returnGeometry": "false", "f": "json"}
    features = json.loads(fetch(f"{service}/identify", parameters)).get("catalogItems", {}).get("features", [])
    aerial = [feature["attributes"] for feature in features if feature["attributes"].get("acq_driver_name") == "SISP"]
    if not aerial:
        return "", ""
    start = time.strftime("%Y-%m-%d", time.gmtime(aerial[0]["capturestart"] / 1000))
    end = time.strftime("%Y-%m-%d", time.gmtime(aerial[0]["captureend"] / 1000))
    return f"{start}/{end}", aerial[0]["name"]


def chip(url, operation, extent):
    parameters = {"bbox": ",".join(str(value) for value in extent), "bboxSR": 3857, "imageSR": 3857,
                  "size": f"{chip_pixels},{chip_pixels}", "format": "png", "f": "image"}
    return Image.open(io.BytesIO(fetch(f"{url}/{operation}", parameters))).convert("RGB")


def outline_cell(image, cell_corners, extent):
    scale = chip_pixels / (extent[2] - extent[0])
    points = [((x - extent[0]) * scale, (extent[3] - y) * scale) for x, y in cell_corners]
    draw = ImageDraw.Draw(image)
    draw.polygon(points, outline=(255, 0, 0), width=2)
    return image


def reference_chips(config=None):
    config = config or load_config()
    grid, _, _ = build_grid(config)
    to_mercator = Transformer.from_crs(grid.crs, "EPSG:3857", always_xy=True)
    samples = read_samples(config)
    recent_service = config["assessment"]["reference_imagery"]
    earlier_service = config["assessment"]["earlier_reference_imagery"]
    records = []
    panels = []
    for sample in samples:
        _, _, (left, bottom, right, top) = grid_cell(sample, grid)
        corners = [to_mercator.transform(x, y) for x, y in ((left, top), (right, top), (right, bottom), (left, bottom))]
        centre_x = sum(x for x, _ in corners) / 4
        centre_y = sum(y for _, y in corners) / 4
        extent = [centre_x - chip_half_width_m, centre_y - chip_half_width_m,
                  centre_x + chip_half_width_m, centre_y + chip_half_width_m]
        recent = outline_cell(chip(recent_service, "export", extent), corners, extent)
        earlier = outline_cell(chip(earlier_service, "exportImage", extent), corners, extent)
        recent_date, recent_source, recent_resolution = imagery_date(recent_service, centre_x, centre_y, extent)
        earlier_dates, earlier_project = earlier_imagery_date(earlier_service, centre_x, centre_y)
        recent.save(work_path("reference_chips", f"{sample['sample_id']}_recent.png"))
        earlier.save(work_path("reference_chips", f"{sample['sample_id']}_earlier.png"))
        records.append({"sample_id": sample["sample_id"], "recent_imagery_date": recent_date,
                        "recent_imagery_source": recent_source, "recent_imagery_resolution_m": recent_resolution,
                        "earlier_imagery_dates": earlier_dates, "earlier_imagery_project": earlier_project})
        panels.append((sample, recent, earlier, recent_date, earlier_dates))
        print(f"{sample['sample_id']}: recent {recent_date} {recent_source}, earlier {earlier_dates}", flush=True)
    with results_path("reference_imagery_dates.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    per_sheet = 8
    for sheet_number in range(0, len(panels), per_sheet):
        group = panels[sheet_number:sheet_number + per_sheet]
        sheet = Image.new("RGB", (2 * (chip_pixels * 2 + 10), 4 * (chip_pixels + 24)), "white")
        draw = ImageDraw.Draw(sheet)
        for position, (sample, recent, earlier, recent_date, earlier_dates) in enumerate(group):
            x = (position % 2) * (chip_pixels * 2 + 10)
            y = (position // 2) * (chip_pixels + 24)
            draw.text((x + 4, y + 4), f"{sample['sample_id']} {sample['place']} | {recent_date} | QLD {earlier_dates[:10]}",
                      fill="black")
            sheet.paste(recent, (x, y + 20))
            sheet.paste(earlier, (x + chip_pixels + 2, y + 20))
        sheet.save(work_path("reference_chips", f"sheet_{sheet_number // per_sheet + 1:02d}.png"))
    update_manifest("reference_chips", {
        "recent_reference_imagery": recent_service,
        "earlier_reference_imagery": earlier_service,
        "chip_half_width_m": chip_half_width_m,
        "samples": len(records),
        "dates_file": "analysis/results/reference_imagery_dates.csv",
        "note": "Chips are stored only in analysis/work/reference_chips for review and are not published.",
    })
