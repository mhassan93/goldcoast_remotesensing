import json
import re
import urllib.request
from collections import defaultdict

from .grid import geometry_bounds, read_boundary_lonlat


def post_json(url, body):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def search_bbox(config):
    return list(geometry_bounds(read_boundary_lonlat(config)))


def search_items(config):
    imagery = config["imagery"]
    url = imagery["stac_api"].rstrip("/") + "/search"
    body = {
        "collections": [imagery["collection"]],
        "bbox": search_bbox(config),
        "datetime": f"{imagery['start']}/{imagery['end']}",
        "limit": 100,
    }
    items = []
    while url:
        page = post_json(url, body)
        items.extend(page["features"])
        next_link = next((link for link in page.get("links", []) if link["rel"] == "next"), None)
        url = next_link["href"] if next_link else None
        body = next_link.get("body", body) if next_link else None
    return items


def relative_orbit(item):
    return int(re.search(r"_R(\d{3})_", item["properties"]["s2:product_uri"]).group(1))


def acquisition_id(datatake_id):
    platform, sensing_time, absolute_orbit = datatake_id.split("_")[:3]
    return f"{platform[1:]}_{sensing_time}_{absolute_orbit}"


def group_acquisitions(items):
    groups = defaultdict(list)
    for item in items:
        groups[item["properties"]["s2:datatake_id"]].append(item)
    acquisitions = []
    for datatake_id, group in groups.items():
        group.sort(key=lambda item: item["properties"]["grid:code"])
        acquisitions.append(
            {
                "id": acquisition_id(datatake_id),
                "datatake_id": datatake_id,
                "datetime": min(item["properties"]["datetime"] for item in group),
                "platform": group[0]["properties"]["platform"],
                "relative_orbit": relative_orbit(group[0]),
                "processing_baseline": group[0]["properties"]["s2:processing_baseline"],
                "items": group,
            }
        )
    return sorted(acquisitions, key=lambda acquisition: acquisition["datetime"])
