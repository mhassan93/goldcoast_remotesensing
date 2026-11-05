import sys


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
    else:
        raise SystemExit(f"Unknown stage '{stage}'")


stage_order = ["plan", "acquire", "composite", "calibrate", "classify", "verify", "export", "assess"]

if __name__ == "__main__":
    requested = sys.argv[1:] or ["--help"]
    if requested[0] in ("-h", "--help"):
        print("Stages: " + ", ".join(stage_order + ["reference-chips", "all"]))
        raise SystemExit(0)
    for name in stage_order if requested == ["all"] else requested:
        print(f"== {name}", flush=True)
        run_stage(name)
