#!/usr/bin/env python3
"""RSVP kit command line.

  python3 rsvp.py run --config config.yaml      run the next scheduled day; report when complete
  python3 rsvp.py dry-run                       full run on bundled sample data with a fake engine
  python3 rsvp.py validate --config config.yaml check a config without calling any engine
  python3 rsvp.py report --measurement DIR      rebuild the report from the run log
  python3 rsvp.py recode-sample --measurement DIR [--n N]
  python3 rsvp.py agreement --measurement DIR --file FILLED.csv
  python3 rsvp.py correct --measurement DIR --run R00001 --field mention --new 1 --reason TEXT
"""

import argparse
import datetime
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import config as config_mod  # noqa: E402
import counter  # noqa: E402
import reporter  # noqa: E402
import runlog  # noqa: E402
import runner  # noqa: E402

SAMPLE_DIR = os.path.join(HERE, "sample")
SAMPLE_CONFIG = os.path.join(SAMPLE_DIR, "config.sample.yaml")
SAMPLE_REPORT = os.path.join(SAMPLE_DIR, "sample_report.md")


def _report(m):
    try:
        reporter.build_report(m)
    except reporter.ReportRefused as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print("report written: %s" % m.path("report.md"))
    print("coded run log:  %s" % m.path("coded_runlog.csv"))
    return 0


def _finished(m):
    return len(m.records()) >= len(m.plan())


def cmd_validate(args):
    cfg = config_mod.load(args.config)
    plan = runner.expand(cfg)
    print("config is valid: %d planned runs (%d locations x %d engines x %d prompts x %d runs)" % (
        len(plan), len(cfg["locations"]), len(cfg["engines"]), len(cfg["prompts"]), cfg["runs_per_prompt"]))
    print("protocol hash: %s" % config_mod.protocol_hash(cfg))
    return 0


def cmd_run(args):
    cfg = config_mod.load(args.config)
    m = runner.run_measurement(cfg, all_days=args.all_days, force=args.force)
    if _finished(m) or args.report:
        return _report(m)
    return 0


def cmd_dry_run(args):
    cfg = config_mod.load(args.config)
    out = os.path.abspath(args.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    cfg["output_dir"] = out
    clock = runner.SimulatedClock(cfg.get("simulated_start_date") or "2026-11-02")
    static = {}
    redirects = cfg.get("simulated_redirects_file")
    if redirects:
        with open(os.path.join(cfg["_base_dir"], redirects), "r", encoding="utf-8") as fh:
            static = json.load(fh)
    resolver = runner.RedirectResolver(enabled=False, static_map=static)
    m = runner.run_measurement(cfg, clock=clock, all_days=True, resolver=resolver, log=print)
    code = _report(m)
    if code == 0 and args.write_sample:
        shutil.copyfile(m.path("report.md"), SAMPLE_REPORT)
        print("sample report updated: %s" % SAMPLE_REPORT)
    return code


def cmd_report(args):
    return _report(runlog.open_measurement(args.measurement))


def cmd_recode_sample(args):
    m = runlog.open_measurement(args.measurement)
    path = args.out or m.path("recode_sample.csv")
    size = counter.write_recode_sample(m, path, fraction=args.fraction, n=args.n, seed=args.seed)
    print("wrote %d runs for blind recoding: %s" % (size, path))
    return 0


def cmd_agreement(args):
    m = runlog.open_measurement(args.measurement)
    out = counter.agreement(m, args.file)
    for field, v in sorted(out["fields"].items()):
        pct = 100.0 * v["agree"] / v["n"] if v["n"] else 0.0
        flag = "  below 90%: rewrite the rules and recode" if v["n"] and pct < 90 else ""
        print("%-9s %5.1f%% (%d of %d)%s" % (field, pct, v["agree"], v["n"], flag))
    print("saved: %s" % m.path("agreement.json"))
    return 0


def cmd_correct(args):
    m = runlog.open_measurement(args.measurement)
    if args.field not in ("mention", "cited", "pos"):
        print("field must be mention, cited or pos", file=sys.stderr)
        return 2
    runs = {r["run"] for r in m.records()}
    if args.run not in runs:
        print("run %s is not in this measurement" % args.run, file=sys.stderr)
        return 2
    rows, _ = counter.code_all(m.records(), m.protocol, m.changes())
    old = next(r for r in rows if r["run"] == args.run)[args.field]
    m.append_change({"run": args.run, "field": args.field, "old": old, "new": int(args.new),
                     "reason": args.reason,
                     "at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()})
    print("change recorded; the original record is kept. Rebuild the report with: rsvp.py report")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rsvp.py", description="RSVP measurement kit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run the next scheduled day; writes the report when complete")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--all-days", action="store_true", help="run every remaining day now (not recommended)")
    p.add_argument("--force", action="store_true", help="run the next day even if today already had runs")
    p.add_argument("--report", action="store_true", help="try to write the report even if runs remain")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("dry-run", help="end-to-end run on bundled sample data with a fake engine")
    p.add_argument("--config", default=SAMPLE_CONFIG)
    p.add_argument("--out", default=os.path.join(HERE, "measurements-dry-run"))
    p.add_argument("--write-sample", action="store_true", help="copy the report to sample/sample_report.md")
    p.set_defaults(func=cmd_dry_run)

    p = sub.add_parser("validate", help="check a config")
    p.add_argument("--config", default="config.yaml")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("report", help="rebuild the report from a measurement's run log")
    p.add_argument("--measurement", required=True)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("recode-sample", help="write a blind sample for a second analyst")
    p.add_argument("--measurement", required=True)
    p.add_argument("--fraction", type=float, default=0.10)
    p.add_argument("--n", type=int, default=None, help="fixed sample size, for example 10 for a dry run check")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_recode_sample)

    p = sub.add_parser("agreement", help="compute agreement from a filled recode sample")
    p.add_argument("--measurement", required=True)
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_agreement)

    p = sub.add_parser("correct", help="record a coding correction in the change list")
    p.add_argument("--measurement", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--field", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_correct)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except config_mod.ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
