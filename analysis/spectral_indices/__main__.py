import sys

from .settings import load_config, select_year

assessment_stages = {"calibrate", "assess", "reference-chips"}
sentinel_stage_order = ["plan", "acquire", "composite", "calibrate", "classify", "verify", "export", "assess"]
dea_stages = ["dea-tiles", "dea-verify"]


def run_stage(stage):
    if stage == "plan":
        from .acquire import plan
        plan()
    elif stage == "acquire":
        from .acquire import acquire
        acquire()
    elif stage == "composite":
        from .composite import composite
        composite()
    elif stage == "calibrate":
        from .assess import calibrate
        calibrate()
    elif stage == "classify":
        from .classify import classify
        classify()
    elif stage == "verify":
        from .verify import verify
        verify()
    elif stage == "export":
        from .export_web import export
        export()
    elif stage == "reference-chips":
        from .reference import reference_chips
        reference_chips()
    elif stage == "assess":
        from .assess import assess
        assess()
    elif stage == "dea-tiles":
        from .dea_land_cover import export_dea_tiles
        export_dea_tiles()
    elif stage == "dea-verify":
        from .dea_land_cover import verify_dea_tiles
        verify_dea_tiles()
    else:
        raise SystemExit(f"Unknown stage '{stage}'")


def split_year(arguments):
    if "--year" not in arguments:
        return None, arguments
    position = arguments.index("--year")
    if position + 1 >= len(arguments) or not arguments[position + 1].isdigit():
        raise SystemExit("--year needs a four-digit year, for example --year 2025")
    return int(arguments[position + 1]), arguments[:position] + arguments[position + 2:]


def requested_stages(stages, year, config):
    is_assessment_year = year == config["assessment"]["year"]
    if stages == ["all"]:
        return [stage for stage in sentinel_stage_order if is_assessment_year or stage not in assessment_stages]
    for stage in stages:
        if stage in assessment_stages and not is_assessment_year:
            raise SystemExit(f"'{stage}' uses reference labels for {config['assessment']['year']} and only runs for that year")
    return stages


if __name__ == "__main__":
    year, stages = split_year(sys.argv[1:])
    if not stages or stages[0] in ("-h", "--help"):
        print("Sentinel-2 stages (need --year): " + ", ".join(sentinel_stage_order + ["reference-chips", "all"]))
        print("DEA Land Cover stages (all configured years): " + ", ".join(dea_stages))
        raise SystemExit(0)
    config = load_config()
    if any(stage not in dea_stages for stage in stages):
        if year not in config["imagery"]["years"]:
            raise SystemExit(f"--year must be one of {config['imagery']['years']}")
        select_year(year)
        stages = requested_stages(stages, year, config)
    for name in stages:
        print(f"== {name}" + (f" {year}" if name not in dea_stages else ""), flush=True)
        run_stage(name)
