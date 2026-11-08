from datetime import datetime, timezone

from .settings import read_json, results_path, write_json


def manifest_path():
    return results_path("processing_manifest.json")


def update_manifest(stage, details):
    path = manifest_path()
    manifest = read_json(path) if path.exists() else {}
    manifest[stage] = {"completed": datetime.now(timezone.utc).isoformat(timespec="seconds"), **details}
    write_json(path, manifest)


def read_manifest():
    path = manifest_path()
    return read_json(path) if path.exists() else {}
