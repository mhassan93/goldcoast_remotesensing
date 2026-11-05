from datetime import datetime, timezone

from .settings import read_json, results_path, write_json

manifest_path = results_path("processing_manifest.json")


def update_manifest(stage, details):
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    manifest[stage] = {"completed": datetime.now(timezone.utc).isoformat(timespec="seconds"), **details}
    write_json(manifest_path, manifest)


def read_manifest():
    return read_json(manifest_path) if manifest_path.exists() else {}
