"""Load and validate an RSVP config, and compute the protocol hash.

The config is the pre-registered protocol. It is validated before any run:
two to four competitors, one intent label per prompt, a need ID per prompt,
no unbranded prompt that names the brand, a location method per engine,
and a positive run count.
"""

import copy
import hashlib
import json
import os
import re

import counter
import yamlsubset

INTENTS = ("informational", "commercial", "transactional")
LOCATION_METHODS = ("setting", "prompt")

# Keys that change how the runner behaves on the wire but not what is
# measured. They are left out of the protocol hash.
OPERATIONAL_KEYS = ("timeout_seconds", "retry_backoff_seconds",
                    "min_seconds_between_calls", "output_dir", "keys_file")

REQUIRED_TOP = ("protocol_id", "brand", "competitors", "engines", "locations",
                "network_location", "runs_per_prompt", "schedule_days",
                "pilot_threshold", "first_measurement", "directional_band_width",
                "remeasure_weeks", "location_sentence")

DEFAULTS = {
    "other_brands": [],
    "extra_public_suffixes": [],
    "seed": 1,
    "timeout_seconds": 60,
    "retry_backoff_seconds": 2,
    "min_seconds_between_calls": 1,
    "resolve_redirects": True,
    "output_dir": "measurements",
    "keys_file": "keys.env",
}


class ConfigError(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("config is not valid:\n  - " + "\n  - ".join(self.problems))


def load(path):
    raw = yamlsubset.load(path)
    if not isinstance(raw, dict):
        raise ConfigError(["the config must be a mapping of keys to values"])
    base = os.path.dirname(os.path.abspath(path))
    if "prompts_file" in raw and raw.get("prompts_file"):
        pfile = raw["prompts_file"]
        if not os.path.isabs(pfile):
            pfile = os.path.join(base, pfile)
        if not os.path.exists(pfile):
            raise ConfigError(["prompts_file %r not found" % raw["prompts_file"]])
        pdata = yamlsubset.load(pfile)
        if "prompts" in raw and raw["prompts"]:
            raise ConfigError(["give prompts inline or in prompts_file, not both"])
        raw["prompts"] = pdata.get("prompts") if isinstance(pdata, dict) else pdata
    raw.pop("prompts_file", None)
    for k, v in DEFAULTS.items():
        raw.setdefault(k, copy.deepcopy(v))
    raw["_base_dir"] = base
    validate(raw)
    return raw


def _is_domain(d):
    return isinstance(d, str) and re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$", d) is not None


def validate(cfg):
    p = []
    for key in REQUIRED_TOP:
        if key not in cfg or cfg[key] is None or cfg[key] == "":
            p.append("missing required key: %s" % key)

    if cfg.get("protocol_id") and not re.match(r"^[A-Za-z0-9._-]+$", str(cfg["protocol_id"])):
        p.append("protocol_id may hold only letters, digits, dot, dash and underscore")

    brand = cfg.get("brand")
    if not isinstance(brand, dict):
        p.append("brand must be a mapping with name, domain, aliases, exclusions")
        raise ConfigError(p)
    for key in ("name", "domain"):
        if not brand.get(key):
            p.append("brand.%s is required" % key)
    brand.setdefault("aliases", [])
    brand.setdefault("exclusions", [])
    if brand.get("aliases") is None:
        brand["aliases"] = []
    if brand.get("exclusions") is None:
        brand["exclusions"] = []
    if brand.get("domain") and not _is_domain(str(brand["domain"]).lower()):
        p.append("brand.domain must be a plain domain such as brand.com, got %r" % brand["domain"])

    comps = cfg.get("competitors") or []
    if not isinstance(comps, list) or not (2 <= len(comps) <= 4):
        p.append("name two to four competitors (found %d)" % (len(comps) if isinstance(comps, list) else 0))
    else:
        for i, c in enumerate(comps):
            if not isinstance(c, dict) or not c.get("name"):
                p.append("competitor %d needs a name" % (i + 1))
                continue
            c.setdefault("aliases", [])
            if c.get("aliases") is None:
                c["aliases"] = []
            if c.get("domain") and not _is_domain(str(c["domain"]).lower()):
                p.append("competitor %s: domain %r is not a plain domain" % (c["name"], c["domain"]))
    others = cfg.get("other_brands") or []
    cfg["other_brands"] = others
    for o in others:
        if not isinstance(o, dict) or not o.get("name"):
            p.append("each other_brands entry needs a name")
        else:
            o.setdefault("aliases", [])
            if o.get("aliases") is None:
                o["aliases"] = []

    names = [brand.get("name")] + [c.get("name") for c in comps if isinstance(c, dict)] \
        + [o.get("name") for o in others if isinstance(o, dict)]
    lowered = [str(n).lower() for n in names if n]
    if len(set(lowered)) != len(lowered):
        p.append("brand, competitor and other brand names must be unique")

    prompts = cfg.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        p.append("the prompt list is empty: give prompts or prompts_file")
        prompts = []
    ids = set()
    client_aliases = [brand.get("name")] + list(brand.get("aliases") or [])
    for i, pr in enumerate(prompts):
        where = "prompt %d" % (i + 1)
        if not isinstance(pr, dict):
            p.append("%s must be a mapping" % where)
            continue
        pid = pr.get("id")
        if not pid:
            p.append("%s has no id" % where)
        elif pid in ids:
            p.append("prompt id %s is used twice" % pid)
        else:
            ids.add(pid)
        where = "prompt %s" % (pid or i + 1)
        if not pr.get("text") or not str(pr.get("text")).strip():
            p.append("%s has no text" % where)
        intent = pr.get("intent")
        if intent not in INTENTS:
            p.append("%s needs exactly one intent label (informational, commercial or transactional), got %r" % (where, intent))
        if not pr.get("need"):
            p.append("%s needs a need ID (give paraphrases of one need the same ID)" % where)
        pr["branded"] = bool(pr.get("branded", False))
        if "eligible" not in pr:
            pr["eligible"] = None
        if pr["eligible"] not in (None, True, False):
            p.append("%s: eligible must be true, false or empty" % where)
        if pr.get("text"):
            names_brand = counter.text_names_any(str(pr["text"]), client_aliases, brand.get("exclusions") or [])
            if names_brand and not pr["branded"]:
                p.append("%s names the client brand: mark it branded: true or remove the name (the headline list is unbranded)" % where)
            if pr["branded"] and not names_brand:
                p.append("%s is marked branded but does not name the client brand" % where)
    if prompts and all(isinstance(pr, dict) and pr.get("branded") for pr in prompts):
        p.append("the headline prompt list is empty: at least one prompt must be unbranded")

    engines = cfg.get("engines") or []
    if not isinstance(engines, list) or not engines:
        p.append("list at least one engine")
        engines = []
    eids = set()
    for i, e in enumerate(engines):
        if not isinstance(e, dict):
            p.append("engine %d must be a mapping" % (i + 1))
            continue
        eid = e.get("id")
        if not eid:
            p.append("engine %d has no id" % (i + 1))
        elif eid in eids:
            p.append("engine id %s is used twice" % eid)
        else:
            eids.add(eid)
        for key in ("adapter", "mode", "interface"):
            if not e.get(key):
                p.append("engine %s: %s is required" % (eid or i + 1, key))
        if e.get("location_method") not in LOCATION_METHODS:
            p.append("engine %s: location_method must be 'setting' or 'prompt'" % (eid or i + 1))
        e.setdefault("options", {})
        if e.get("options") is None:
            e["options"] = {}

    locs = cfg.get("locations") or []
    if not isinstance(locs, list) or not locs:
        p.append("declare at least one location")
        locs = []
    labels = set()
    for i, loc in enumerate(locs):
        if not isinstance(loc, dict) or not loc.get("label"):
            p.append("location %d needs a label such as 'United States' or 'Boise, Idaho, United States'" % (i + 1))
            continue
        if loc["label"] in labels:
            p.append("location %s is declared twice" % loc["label"])
        labels.add(loc["label"])

    for key in ("runs_per_prompt", "schedule_days", "pilot_threshold", "remeasure_weeks"):
        v = cfg.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            p.append("%s must be a positive whole number" % key)
    if isinstance(cfg.get("schedule_days"), int) and isinstance(cfg.get("runs_per_prompt"), int) \
            and cfg["schedule_days"] > cfg["runs_per_prompt"]:
        p.append("schedule_days cannot exceed runs_per_prompt (each day needs at least one run of every cell)")
    v = cfg.get("directional_band_width")
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        p.append("directional_band_width must be a positive number of percentage points")
    if not isinstance(cfg.get("first_measurement"), bool):
        p.append("first_measurement must be true or false")
    if "{location}" not in str(cfg.get("location_sentence", "")):
        p.append("location_sentence must contain {location}")

    if p:
        raise ConfigError(p)

    # Validate adapters last so that config errors are reported first.
    import engines as engine_registry
    for e in engines:
        try:
            adapter_cls = engine_registry.get_adapter_class(e["adapter"])
        except KeyError as exc:
            p.append(str(exc).strip("'\""))
            continue
        if e["location_method"] == "setting" and not adapter_cls.supports_location_setting:
            p.append("engine %s: adapter %s has no location setting, use location_method: prompt" % (e["id"], e["adapter"]))
        for msg in adapter_cls.validate_engine(e):
            p.append("engine %s: %s" % (e["id"], msg))
    if p:
        raise ConfigError(p)


def protocol(cfg):
    """The part of the config that defines the measurement."""
    snap = {k: copy.deepcopy(v) for k, v in cfg.items()
            if not k.startswith("_") and k not in OPERATIONAL_KEYS}
    return snap


def protocol_hash(cfg):
    canon = json.dumps(protocol(cfg), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def changed_sections(old_protocol, new_protocol):
    keys = sorted(set(old_protocol) | set(new_protocol))
    changed = [k for k in keys if old_protocol.get(k) != new_protocol.get(k)]
    detail = []
    ob, nb = old_protocol.get("brand") or {}, new_protocol.get("brand") or {}
    for sub in ("aliases", "exclusions", "name", "domain"):
        if ob.get(sub) != nb.get(sub):
            detail.append("brand." + sub)
    return changed, detail


def notices(cfg):
    """Non-fatal notes on settings outside the working ranges in the RSVP docs.

    The ranges are working ranges, not rules: three to six engines (Engines and
    location page) and four to eight unbranded prompts per intent (Prompt list
    and intent page). The kit still runs outside them.
    """
    out = []
    n_eng = len(cfg.get("engines") or [])
    if n_eng < 3 or n_eng > 6:
        out.append("%d engines is outside the working range of three to six" % n_eng)
    counts = {"informational": 0, "commercial": 0, "transactional": 0}
    for pr in cfg.get("prompts") or []:
        if isinstance(pr, dict) and not pr.get("branded") and pr.get("intent") in counts:
            counts[pr["intent"]] += 1
    for intent, n in counts.items():
        if n < 4 or n > 8:
            out.append("%d unbranded %s prompts is outside the working range of four to eight per intent" % (n, intent))
    return out
