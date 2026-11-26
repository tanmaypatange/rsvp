"""The runner: sends every location x engine x prompt x run in a fresh context.

For each planned run it sends the prompt once per attempt, with no earlier
messages and no follow-up, and stores the answer, the cited sources, the
time and any error as one append-only row before doing anything else.
Only technical failures (error, empty body, timeout) are retried, up to
three attempts with growing waits. An answer is never retried because of
what it says. Runs are spread across the scheduled days and shuffled
within each day.
"""

import datetime
import os
import random
import time
import urllib.request

import engines as engine_registry
import runlog

MAX_ATTEMPTS = 3


def expand(cfg):
    """The plan in loop order: location, engine, prompt, run number."""
    plan = []
    days = cfg["schedule_days"]
    runs = cfg["runs_per_prompt"]
    n = 0
    for loc in cfg["locations"]:
        for eng in cfg["engines"]:
            for pr in cfg["prompts"]:
                for r in range(1, runs + 1):
                    n += 1
                    plan.append({
                        "run": "R%05d" % n,
                        "location": loc["label"],
                        "engine": eng["id"],
                        "prompt": pr["id"],
                        "run_number": r,
                        # Spread each cell evenly across the days.
                        "day": ((r - 1) * days) // runs + 1,
                    })
    return plan


def schedule(plan, seed):
    """Order runs by day, shuffled within each day so no prompt or engine is always first."""
    out = []
    for day in sorted({p["day"] for p in plan}):
        todays = [p for p in plan if p["day"] == day]
        random.Random("%s-%d" % (seed, day)).shuffle(todays)
        out.extend(todays)
    for i, p in enumerate(out):
        p["order"] = i + 1
    return out


def load_keys(path):
    keys = dict(os.environ)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys


class RealClock:
    def now(self):
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

    def sleep(self, seconds):
        if seconds > 0:
            time.sleep(seconds)

    def start_day(self, day):
        pass


class SimulatedClock:
    """For the dry run: scheduled day d is start_date + d - 1, no real waiting."""

    def __init__(self, start_date):
        self.start = datetime.datetime.combine(
            datetime.date.fromisoformat(start_date), datetime.time(9, 0),
            tzinfo=datetime.timezone.utc)
        self.current = self.start

    def now(self):
        return self.current

    def sleep(self, seconds):
        self.current += datetime.timedelta(seconds=max(seconds, 0))

    def start_day(self, day):
        self.current = max(self.current, self.start + datetime.timedelta(days=day - 1))
        self.current = self.current.replace(hour=max(self.current.hour, 9))


class RedirectResolver:
    """Follows redirects with HEAD requests. Keeps the raw URL when resolution fails."""

    def __init__(self, enabled=True, static_map=None, timeout=10):
        self.enabled = enabled
        self.static = static_map or {}
        self.timeout = timeout
        self.cache = {}

    def resolve(self, url):
        if url in self.static:
            return self.static[url]
        if not self.enabled:
            return None
        if url in self.cache:
            return self.cache[url]
        result = None
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                final = resp.geturl()
                result = final if final != url else None
        except Exception:
            result = None
        self.cache[url] = result
        return result


def prompt_text_for(prompt, location, engine_cfg, cfg):
    if engine_cfg["location_method"] == "prompt":
        return cfg["location_sentence"].format(location=location["label"]) + " " + prompt["text"]
    return prompt["text"]


def run_measurement(cfg, clock=None, all_days=False, resolver=None, log=print, force=False):
    """Run the next scheduled day (or every remaining day). Returns the Measurement."""
    clock = clock or RealClock()
    plan = schedule(expand(cfg), cfg["seed"])
    m, new, note = runlog.start_or_resume(cfg, plan, now=clock.now().isoformat())
    log(note)
    plan = m.plan()
    done = {r["run"] for r in m.records()}
    pending = [p for p in plan if p["run"] not in done]
    if not pending:
        log("all %d planned runs are in the log" % len(plan))
        return m
    keys = load_keys(os.path.join(cfg["_base_dir"], cfg["keys_file"]))
    resolver = resolver or RedirectResolver(enabled=cfg["resolve_redirects"])
    engines = {e["id"]: e for e in cfg["engines"]}
    adapters = {eid: engine_registry.make_adapter(e, keys, cfg["_base_dir"]) for eid, e in engines.items()}
    prompts = {p["id"]: p for p in cfg["prompts"]}
    locations = {loc["label"]: loc for loc in cfg["locations"]}
    stopped = {d["engine"] for d in m.deviations() if d.get("kind") == "engine_stopped"}
    spacing = {eid: float(cfg["min_seconds_between_calls"]) for eid in engines}
    last_call = {}

    days = sorted({p["day"] for p in pending})
    if not all_days:
        records = m.records()
        last_dates = sorted(r["sent_at"][:10] for r in records)
        today = clock.now().date().isoformat()
        if records and not force and last_dates[-1] == today and min(days) > max(r["day"] for r in records):
            log("day %d is scheduled for a later date than today's runs; run again on another day "
                "(spreading runs across days is part of the method)" % min(days))
            return m
        days = days[:1]

    for day in days:
        clock.start_day(day)
        todays = [p for p in pending if p["day"] == day]
        log("day %d: %d runs" % (day, len(todays)))
        for p in todays:
            if p["engine"] in stopped:
                continue
            eng = engines[p["engine"]]
            prompt = prompts[p["prompt"]]
            loc = locations[p["location"]]
            text = prompt_text_for(prompt, loc, eng, cfg)
            wait = spacing[p["engine"]] - (time.monotonic() - last_call.get(p["engine"], -1e9))
            if isinstance(clock, RealClock):
                clock.sleep(wait)
            else:
                clock.sleep(spacing[p["engine"]])
            errors = []
            resp = None
            sent_at = clock.now()
            try:
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    req = engine_registry.EngineRequest(p["prompt"], text, loc, eng["location_method"],
                                                        p["run_number"], attempt, cfg["timeout_seconds"])
                    try:
                        resp = adapters[p["engine"]].call(req)
                    except engine_registry.LocationSettingUnavailable:
                        raise
                    except Exception as exc:  # an adapter bug or a missing key is a technical failure
                        resp = engine_registry.EngineResponse("error", error="%s: %s" % (type(exc).__name__, exc))
                    last_call[p["engine"]] = time.monotonic()
                    if resp.status in ("ok", "refused"):
                        break
                    errors.append({"attempt": attempt, "status": resp.status, "error": resp.error})
                    if resp.rate_limited:
                        spacing[p["engine"]] = max(spacing[p["engine"]] * 2, 1.0)
                        log("engine %s signalled a rate limit; slowing to one call per %.0f s"
                            % (p["engine"], spacing[p["engine"]]))
                    if attempt < MAX_ATTEMPTS:
                        clock.sleep(cfg["retry_backoff_seconds"] * (2 ** (attempt - 1)))
            except engine_registry.LocationSettingUnavailable as exc:
                stopped.add(p["engine"])
                m.append_deviation({"kind": "engine_stopped", "engine": p["engine"],
                                    "at": clock.now().isoformat(),
                                    "reason": "location setting unavailable: %s" % exc,
                                    "note": "the runner does not switch to the prompt sentence silently"})
                log("engine %s stopped: its location setting is unavailable (deviation logged)" % p["engine"])
                continue
            sources = []
            for s in resp.sources:
                s = dict(s)
                if s.get("url"):
                    resolved = resolver.resolve(s["url"])
                    if resolved:
                        s["resolved_url"] = resolved
                sources.append(s)
            record = {
                "run": p["run"],
                "measurement_id": m.id,
                "config_hash": m.manifest["config_hash"],
                "protocol_id": cfg["protocol_id"],
                "order": p["order"],
                "day": p["day"],
                "engine": p["engine"],
                "engine_detail": {k: eng.get(k) for k in ("adapter", "model", "mode", "interface")},
                "location": p["location"],
                "location_method": eng["location_method"],
                "network_location": cfg["network_location"],
                "prompt": p["prompt"],
                "need": prompt["need"],
                "intent": prompt["intent"],
                "branded": prompt["branded"],
                "eligible": prompt.get("eligible"),
                "prompt_text": text,
                "run_number": p["run_number"],
                "sent_at": sent_at.isoformat(),
                "received_at": clock.now().isoformat(),
                "request_summary": resp.request_summary,
                "status": resp.status,
                "answer_text": resp.text,
                "sources": sources,
                "sponsored": resp.sponsored,
                "search_indicated": resp.search_indicated,
                "served_model": resp.served_model,
                "error_detail": resp.error if resp.status not in ("ok", "refused") else None,
                "attempt": len(errors) + 1 if resp.status in ("ok", "refused") else len(errors),
                "attempt_errors": errors,
            }
            m.append_record(record)
    remaining = len(plan) - len(m.records())
    if remaining and not all_days:
        log("%d planned runs remain for later days; run the same command again on the next day" % remaining)
    return m
