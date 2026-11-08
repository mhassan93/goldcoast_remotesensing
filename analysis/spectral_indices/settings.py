import json
import tomllib
from pathlib import Path

package_root = Path(__file__).resolve().parent
analysis_root = package_root.parent
project_root = analysis_root.parent
config_path = analysis_root / "config.toml"
work_base = analysis_root / "work"
results_base = analysis_root / "results"
selection = {"year": None}


def select_year(year):
    selection["year"] = year


def selected_year():
    if selection["year"] is None:
        raise SystemExit("Choose a Sentinel-2 year with --year, for example --year 2025")
    return selection["year"]


def load_config():
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)
    year = selection["year"]
    if year is not None:
        config["year"] = year
        config["imagery"]["start"] = f"{year}-01-01T00:00:00Z"
        config["imagery"]["end"] = f"{year}-12-31T23:59:59.999Z"
        config["web"]["output"] = config["web"]["output"].format(year=year)
    return config


def created_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def work_path(*parts):
    return created_parent((work_base / str(selected_year())).joinpath(*parts))


def results_path(*parts):
    return created_parent((results_base / str(selected_year())).joinpath(*parts))


def shared_work_path(*parts):
    return created_parent(work_base.joinpath(*parts))


def shared_results_path(*parts):
    return created_parent(results_base.joinpath(*parts))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".partial")
    temporary_path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    temporary_path.replace(path)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))
