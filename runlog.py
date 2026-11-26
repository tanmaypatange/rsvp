"""The run log: one row per run, append only.

Layout under the output directory:
  index.jsonl                     one row per measurement start (append only)
  <measurement_id>/manifest.json  protocol hash, code version, plan counts
  <measurement_id>/protocol.json  the protocol as hashed at the start
  <measurement_id>/runlog.jsonl   one row per run, never edited
  <measurement_id>/changes.jsonl  corrections to the coding (append only)
  <measurement_id>/deviations.jsonl  deviations found while running

A measurement ID is the protocol_id plus a sequence number. When a config
with the same protocol_id hashes differently (for example, aliases were
added after the first run) a new measurement ID starts, and the change is
recorded in the index. Runs of two measurement IDs are never mixed.
"""

import datetime
import json
import os

import config as config_mod

CODE_VERSION = "0.1.1"
METHOD_VERSION = "RSVP v0.1"


def _append_jsonl(path, row):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                raise ValueError("%s line %d is not valid JSON; the log must not be edited by hand" % (path, n))
    return rows


class Measurement:
    def __init__(self, root, measurement_id):
        self.root = root
        self.id = measurement_id
        self.dir = os.path.join(root, measurement_id)

    def path(self, name):
        return os.path.join(self.dir, name)

    @property
    def manifest(self):
        with open(self.path("manifest.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)

    @property
    def protocol(self):
        with open(self.path("protocol.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def plan(self):
        with open(self.path("plan.json"), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def records(self):
        return read_jsonl(self.path("runlog.jsonl"))

    def changes(self):
        return read_jsonl(self.path("changes.jsonl"))

    def deviations(self):
        return read_jsonl(self.path("deviations.jsonl"))

    def append_record(self, record):
        if record.get("measurement_id") != self.id:
            raise ValueError("record belongs to another measurement")
        _append_jsonl(self.path("runlog.jsonl"), record)

    def append_change(self, change):
        _append_jsonl(self.path("changes.jsonl"), change)

    def append_deviation(self, deviation):
        _append_jsonl(self.path("deviations.jsonl"), deviation)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def start_or_resume(cfg, plan, now=None):
    """Return (Measurement, started_new, note). Hashes the config at the start."""
    root = cfg["output_dir"]
    if not os.path.isabs(root):
        root = os.path.join(cfg["_base_dir"], root)
    os.makedirs(root, exist_ok=True)
    index_path = os.path.join(root, "index.jsonl")
    entries = [e for e in read_jsonl(index_path) if e["protocol_id"] == cfg["protocol_id"]]
    proto = config_mod.protocol(cfg)
    h = config_mod.protocol_hash(cfg)
    if entries and entries[-1]["config_hash"] == h:
        m = Measurement(root, entries[-1]["measurement_id"])
        return m, False, "resuming measurement %s" % m.id
    seq = len(entries) + 1
    mid = "%s-m%d" % (cfg["protocol_id"], seq)
    note = "starting measurement %s" % mid
    changed, detail = [], []
    if entries:
        prev = Measurement(root, entries[-1]["measurement_id"])
        changed, detail = config_mod.changed_sections(prev.protocol, proto)
        note = ("the protocol changed since %s (%s); starting new measurement %s. "
                "Runs of the two measurements are not mixed." % (prev.id, ", ".join(detail or changed), mid))
    m = Measurement(root, mid)
    os.makedirs(m.dir, exist_ok=False)
    started = now or _now()
    with open(m.path("protocol.json"), "w", encoding="utf-8") as fh:
        json.dump(proto, fh, ensure_ascii=False, sort_keys=True, indent=1)
    with open(m.path("plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=0)
    manifest = {
        "measurement_id": mid,
        "protocol_id": cfg["protocol_id"],
        "config_hash": h,
        "code_version": CODE_VERSION,
        "method_version": METHOD_VERSION,
        "started_at": started,
        "planned_runs": len(plan),
        "network_location": cfg["network_location"],
        "previous_measurement": entries[-1]["measurement_id"] if entries else None,
        "changed_sections": changed,
        "changed_detail": detail,
    }
    with open(m.path("manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, sort_keys=True, indent=1)
    for name in ("runlog.jsonl", "changes.jsonl", "deviations.jsonl"):
        open(m.path(name), "a").close()
    _append_jsonl(index_path, {"measurement_id": mid, "protocol_id": cfg["protocol_id"],
                               "config_hash": h, "started_at": started,
                               "changed_sections": changed, "changed_detail": detail})
    return m, True, note


def open_measurement(path):
    path = os.path.abspath(path.rstrip("/"))
    return Measurement(os.path.dirname(path), os.path.basename(path))
