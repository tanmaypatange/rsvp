"""Test helpers: build small configs and measurements in a temporary folder."""

import copy
import json
import os
import shutil
import tempfile

import config as config_mod
import runner

BASE = {
    "protocol_id": "t",
    "brand": {"name": "Acme Books", "domain": "acmebooks.example",
              "aliases": ["Acme", "AcmeBooks"], "exclusions": ["Acme Capital"]},
    "competitors": [{"name": "Birch Ledger", "domain": "birchledger.example"},
                    {"name": "Cedar Accounts", "domain": "cedaraccounts.example"}],
    "other_brands": [{"name": "Dune Pay"}, {"name": "Elm Tax"}],
    "prompts": [
        {"id": "P1", "need": "N1", "intent": "commercial", "text": "Best bookkeeping app for a bakery"},
        {"id": "P2", "need": "N2", "intent": "informational", "text": "How do I track receipts?"},
    ],
    "engines": [{"id": "e1", "label": "Engine One", "adapter": "fake", "model": "m1", "mode": "search-on",
                 "interface": "api", "location_method": "setting",
                 "options": {"canned_file": "canned.json"}}],
    "locations": [{"label": "United States", "country": "US"}],
    "network_location": "test network",
    "location_sentence": "I am in {location}.",
    "runs_per_prompt": 4,
    "schedule_days": 2,
    "seed": 1,
    "pilot_threshold": 10,
    "first_measurement": True,
    "directional_band_width": 20,
    "remeasure_weeks": 4,
    "retry_backoff_seconds": 0,
    "min_seconds_between_calls": 0,
    "resolve_redirects": False,
}


def ok(text, sources=(), **kw):
    e = {"status": "ok", "text": text, "sources": [{"url": u} for u in sources]}
    e.update(kw)
    return e


class Workspace:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="rsvp-test-")

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def config(self, canned, **overrides):
        cfg = copy.deepcopy(BASE)
        for k, v in overrides.items():
            cfg[k] = v
        with open(os.path.join(self.dir, "canned.json"), "w", encoding="utf-8") as fh:
            json.dump(canned, fh)
        cfg.update({k: v for k, v in config_mod.DEFAULTS.items() if k not in cfg})
        cfg["_base_dir"] = self.dir
        cfg["output_dir"] = os.path.join(self.dir, "out")
        config_mod.validate(cfg)
        return cfg

    def run(self, canned, start="2026-11-02", resolver=None, **overrides):
        cfg = self.config(canned, **overrides)
        clock = runner.SimulatedClock(start)
        m = runner.run_measurement(cfg, clock=clock, all_days=True,
                                   resolver=resolver or runner.RedirectResolver(enabled=False),
                                   log=lambda *a: None)
        return cfg, m


def canned_all(answers, engines=("e1",), prompts=("P1", "P2")):
    """Same list of answers for every engine and prompt."""
    return {e: {p: answers for p in prompts} for e in engines}
