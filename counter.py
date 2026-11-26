"""The counter: turns stored run records into coded run-log rows.

Rules applied (from the Mention, Citation and Position pages):
- Mention is a true or false flag per run: the brand name or a pre-listed
  alias appears in the answer text, whole words only, after the exclusion
  list is applied. A run counts once however often the name appears.
- Citation is a match of the client's registrable domain among the cited
  sources, subdomains included, after tracking parameters are stripped and
  redirects resolved. Two pages of one domain are one citation.
- Ghost citation: cited and not mentioned.
- Position: the client's place in the list of brands named, ordered by
  first appearance, in three exclusive bands, only for runs with a mention.
- Failed runs (error, empty body, timeout) are not valid. A refusal in text
  is a valid run with no mention. A run with no citations stays valid.
"""

import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

VALID_STATUSES = ("ok", "refused")
FAILED_STATUSES = ("error", "empty", "timeout")
ALL_STATUSES = VALID_STATUSES + FAILED_STATUSES

POSITION_BANDS = ("first", "second_third", "fourth_later")
POSITION_LABELS = {"first": "1st named", "second_third": "2nd or 3rd", "fourth_later": "4th or later"}

TRACKING_PARAMS = {
    "gclid", "dclid", "gbraid", "wbraid", "fbclid", "msclkid", "yclid",
    "mc_cid", "mc_eid", "igshid", "_hsenc", "_hsmi", "mkt_tok", "ref_src",
    "ref", "spm", "srsltid", "_ga", "_gl",
}
TRACKING_PREFIXES = ("utm_",)

# Multi-label public suffixes. A built-in subset; extend it per measurement
# with extra_public_suffixes in the config.
MULTI_LABEL_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "me.uk", "ltd.uk", "plc.uk", "net.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.nz", "org.nz", "net.nz", "govt.nz",
    "co.jp", "ne.jp", "or.jp", "ac.jp", "go.jp",
    "co.in", "net.in", "org.in", "gov.in", "ac.in",
    "com.br", "net.br", "org.br", "gov.br",
    "com.mx", "org.mx", "gob.mx",
    "co.za", "org.za", "gov.za",
    "com.sg", "edu.sg", "gov.sg",
    "com.cn", "net.cn", "org.cn", "gov.cn",
    "com.hk", "org.hk", "com.tw", "org.tw",
    "co.kr", "or.kr", "com.tr", "com.ar", "com.co", "com.pe",
    "co.il", "org.il", "com.my", "com.ph", "com.vn", "co.id", "co.th",
    "com.es", "com.pl", "co.at", "or.at", "com.ua", "com.eg", "com.sa",
    "com.ng", "co.ke",
}

_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
_QUOTES = {ord("\u2018"): "'", ord("\u2019"): "'", ord("\u201a"): "'", ord("\u201b"): "'",
           ord("\u201c"): '"', ord("\u201d"): '"', ord("\u201e"): '"', ord("\u00ab"): '"',
           ord("\u00bb"): '"'}


def normalise(text):
    """Fold case, normalise quotes and dashes. Keeps length so positions line up."""
    t = unicodedata.normalize("NFC", text or "")
    t = t.translate(_DASHES).translate(_QUOTES)
    t = t.replace("\u00a0", " ")
    folded = []
    for ch in t:
        f = ch.casefold()
        folded.append(f if len(f) == 1 else ch.lower())
    return "".join(folded)


def _pattern(name):
    parts = [re.escape(w) for w in normalise(name).split()]
    if not parts:
        return None
    return re.compile(r"(?<![\w])" + r"\s+".join(parts) + r"(?![\w])")


def _mask(text, spans):
    chars = list(text)
    for s, e in spans:
        for i in range(s, e):
            chars[i] = " "
    return "".join(chars)


def _excluded_spans(norm_text, exclusions):
    spans = []
    for ex in exclusions or []:
        pat = _pattern(ex)
        if pat:
            spans.extend(m.span() for m in pat.finditer(norm_text))
    return spans


def text_names_any(text, aliases, exclusions):
    norm = _mask(normalise(text), _excluded_spans(normalise(text), exclusions))
    for a in aliases:
        pat = _pattern(a) if a else None
        if pat and pat.search(norm):
            return True
    return False


def brand_table(protocol):
    """All brands in matching order: client, named competitors, other brands."""
    b = protocol["brand"]
    table = [{"name": b["name"], "kind": "client",
              "aliases": _dedupe([b["name"]] + list(b.get("aliases") or [])),
              "exclusions": list(b.get("exclusions") or [])}]
    for c in protocol["competitors"]:
        table.append({"name": c["name"], "kind": "competitor",
                      "aliases": _dedupe([c["name"]] + list(c.get("aliases") or [])),
                      "exclusions": list(c.get("exclusions") or [])})
    for o in protocol.get("other_brands") or []:
        table.append({"name": o["name"], "kind": "other",
                      "aliases": _dedupe([o["name"]] + list(o.get("aliases") or [])),
                      "exclusions": list(o.get("exclusions") or [])})
    return table


def _dedupe(items):
    seen, out = set(), []
    for i in items:
        k = normalise(str(i)).strip()
        if k and k not in seen:
            seen.add(k)
            out.append(str(i))
    return out


def find_brands(answer_text, brands, prompt_text=None):
    """Return brands named in the answer, ordered by first appearance.

    Each brand's exclusions are masked for that brand only. A restatement of
    the prompt inside the answer is masked, because a name inside the quoted
    question is not the engine's own answer. Longer aliases win when two
    aliases overlap, so one span of text names at most one brand.
    """
    norm = normalise(answer_text)
    texts = [prompt_text] if isinstance(prompt_text, str) else list(prompt_text or [])
    for t in texts:
        pnorm = normalise(t or "").strip()
        if pnorm:
            spans = []
            start = norm.find(pnorm)
            while start != -1:
                spans.append((start, start + len(pnorm)))
                start = norm.find(pnorm, start + 1)
            norm = _mask(norm, spans)
    candidates = []
    for bi, brand in enumerate(brands):
        masked = _mask(norm, _excluded_spans(norm, brand["exclusions"]))
        for alias in brand["aliases"]:
            pat = _pattern(alias)
            if not pat:
                continue
            for m in pat.finditer(masked):
                candidates.append((m.start(), m.end(), bi))
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0], c[2]))
    claimed = []
    first = {}
    for s, e, bi in candidates:
        if any(s < ce and cs < e for cs, ce in claimed):
            continue
        claimed.append((s, e))
        if bi not in first or s < first[bi]:
            first[bi] = s
    order = sorted(first, key=lambda bi: (first[bi], bi))
    return [brands[bi]["name"] for bi in order]


def position_band(pos):
    if pos <= 0:
        return None
    if pos == 1:
        return "first"
    if pos <= 3:
        return "second_third"
    return "fourth_later"


def strip_tracking(url):
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in TRACKING_PARAMS and not k.lower().startswith(TRACKING_PREFIXES)]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                       urlencode(query, doseq=True), ""))


def host_of(url):
    u = url.strip()
    if "://" not in u:
        u = "http://" + u
    try:
        host = urlsplit(u).hostname or ""
    except ValueError:
        return ""
    return host.rstrip(".").lower()


def registrable_domain(host, extra_suffixes=()):
    host = (host or "").rstrip(".").lower()
    if not host:
        return ""
    if re.match(r"^\d+(\.\d+){3}$", host) or ":" in host:
        return host
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    suffixes = MULTI_LABEL_SUFFIXES | {s.lower().strip(".") for s in extra_suffixes or ()}
    last_two = ".".join(labels[-2:])
    if last_two in suffixes:
        return ".".join(labels[-3:])
    last_three = ".".join(labels[-3:])
    if len(labels) >= 4 and last_three in suffixes:
        return ".".join(labels[-4:])
    return last_two


def clean_source(source, extra_suffixes=()):
    """source is a dict with 'url' and optional 'resolved_url' (set by the runner)."""
    url = source.get("resolved_url") or source.get("url") or ""
    clean = strip_tracking(url)
    domain = registrable_domain(host_of(clean), extra_suffixes)
    return {"raw_url": source.get("url"), "clean_url": clean, "domain": domain}


def code_record(record, protocol):
    """Code one run record into one run-log row."""
    brands = brand_table(protocol)
    client = brands[0]["name"]
    competitor_names = [b["name"] for b in brands if b["kind"] == "competitor"]
    extra = protocol.get("extra_public_suffixes") or []
    client_domain = registrable_domain(protocol["brand"]["domain"], extra)
    status = record.get("status")
    valid = status in VALID_STATUSES
    row = {
        "run": record["run"],
        "measurement_id": record.get("measurement_id"),
        "date": (record.get("sent_at") or "")[:10],
        "day": record.get("day"),
        "engine": record["engine"],
        "location": record["location"],
        "prompt": record["prompt"],
        "need": record.get("need"),
        "intent": record.get("intent"),
        "branded": bool(record.get("branded")),
        "eligible": record.get("eligible"),
        "run_number": record.get("run_number"),
        "status": status,
        "valid": valid,
        "brands": [],
        "mention": False,
        "cited": False,
        "ghost": False,
        "pos": 0,
        "pos_band": None,
        "comp": [],
        "domains": [],
        "search_indicated": record.get("search_indicated"),
        "served_model": record.get("served_model"),
    }
    if not valid:
        return row
    text = record.get("answer_text") or ""
    prompt_texts = [record.get("prompt_text")]
    for pr in protocol.get("prompts") or []:
        if pr.get("id") == record.get("prompt"):
            prompt_texts.append(pr.get("text"))
    named = find_brands(text, brands, prompt_text=prompt_texts)
    domains = []
    for s in record.get("sources") or []:
        d = clean_source(s, extra)["domain"]
        if d and d not in domains:
            domains.append(d)
    row["brands"] = named
    row["mention"] = client in named
    row["cited"] = client_domain in domains
    row["ghost"] = row["cited"] and not row["mention"]
    row["pos"] = named.index(client) + 1 if row["mention"] else 0
    row["pos_band"] = position_band(row["pos"])
    row["comp"] = [n for n in named if n in competitor_names]
    row["domains"] = domains
    return row


def apply_changes(rows, changes):
    """Apply the change list on top of the coding. The original record is kept."""
    by_run = {r["run"]: r for r in rows}
    applied = []
    for ch in changes:
        r = by_run.get(ch["run"])
        if r is None or not r["valid"]:
            continue
        field, new = ch["field"], ch["new"]
        if field in ("mention", "cited"):
            r[field] = bool(new)
        elif field == "pos":
            r["pos"] = int(new)
            r["pos_band"] = position_band(r["pos"])
        else:
            continue
        if field == "mention" and not r["mention"]:
            r["pos"], r["pos_band"] = 0, None
        if field == "mention" and r["mention"] and r["pos"] == 0:
            raise ValueError("change for run %s sets mention without a position; add a pos change first" % r["run"])
        r["ghost"] = r["cited"] and not r["mention"]
        applied.append(ch)
    return applied


def code_all(records, protocol, changes=()):
    rows = [code_record(r, protocol) for r in records]
    applied = apply_changes(rows, list(changes))
    return rows, applied


# ---------------------------------------------------------------- quality checks

RECODE_FIELDS = ("mention", "cited", "pos_band")


def write_recode_sample(measurement, path, fraction=0.10, n=None, seed=1):
    """Write a blind sample of valid runs for a second analyst to code by hand.

    The file holds the answer and sources but not the counter's coding.
    The kit cannot do the coding; it writes the file and computes agreement.
    """
    import csv
    import random
    rows, _ = code_all(measurement.records(), measurement.protocol, measurement.changes())
    valid = sorted((r["run"] for r in rows if r["valid"]))
    if not valid:
        raise ValueError("no valid runs to sample")
    size = n if n else max(1, int(round(len(valid) * fraction)))
    size = min(size, len(valid))
    chosen = set(random.Random(seed).sample(valid, size))
    extra = measurement.protocol.get("extra_public_suffixes") or []
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(("run", "engine", "prompt", "prompt_text", "answer_text", "sources",
                    "mention (1 or 0)", "cited (1 or 0)", "pos_band (first, second_third, fourth_later or blank)"))
        for rec in measurement.records():
            if rec["run"] in chosen:
                srcs = " ".join(clean_source(s, extra)["clean_url"] for s in rec.get("sources") or [])
                w.writerow((rec["run"], rec["engine"], rec["prompt"], rec.get("prompt_text", ""),
                            rec.get("answer_text", ""), srcs, "", "", ""))
    return size


def agreement(measurement, filled_path):
    """Compare a second analyst's coding with the counter's, per field."""
    import csv
    import datetime
    import json
    rows, _ = code_all(measurement.records(), measurement.protocol, measurement.changes())
    by_run = {r["run"]: r for r in rows}
    result = {f: {"agree": 0, "n": 0} for f in RECODE_FIELDS}
    disagreements = []
    count = 0
    with open(filled_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for line in reader:
            if not line or not line[0].strip():
                continue
            rec = dict(zip(("run", "engine", "prompt", "prompt_text", "answer_text", "sources",
                            "mention", "cited", "pos_band"), line))
            row = by_run.get(rec["run"])
            if row is None:
                raise ValueError("run %s is not in this measurement" % rec["run"])
            human = {
                "mention": rec["mention"].strip() in ("1", "yes", "true"),
                "cited": rec["cited"].strip() in ("1", "yes", "true"),
                "pos_band": rec["pos_band"].strip() or None,
            }
            if rec["mention"].strip() == "" or rec["cited"].strip() == "":
                raise ValueError("run %s is not fully coded" % rec["run"])
            count += 1
            for f in RECODE_FIELDS:
                result[f]["n"] += 1
                if human[f] == row[f]:
                    result[f]["agree"] += 1
                else:
                    disagreements.append({"run": rec["run"], "field": f,
                                          "counter": row[f], "analyst": human[f]})
    out = {"sample_size": count, "fields": result, "disagreements": disagreements,
           "computed_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()}
    with open(measurement.path("agreement.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    return out
