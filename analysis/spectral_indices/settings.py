import json
import tomllib
from pathlib import Path

package_root = Path(__file__).resolve().parent
analysis_root = package_root.parent
project_root = analysis_root.parent
config_path = analysis_root / "config.toml"
work_root = analysis_root / "work"
results_root = analysis_root / "results"


def load_config():
    with config_path.open("rb") as config_file:
        return tomllib.load(config_file)


def work_path(*parts):
    path = work_root.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def results_path(*parts):
    path = results_root.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".partial")
    temporary_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    temporary_path.replace(path)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))
