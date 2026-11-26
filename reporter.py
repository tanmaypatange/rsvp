"""The reporter: computes every figure from the run log and fills the report.

Every number in the report comes from the coded run log. The template has
a fixed slot per reporting rule; the reporter refuses to write a report
when a slot is empty or when the method says a figure cannot be given.

Refusal conditions:
- the run log is empty, or holds rows of another measurement or config hash;
- planned runs are missing and no logged deviation explains them;
- a prompt lacks one of the three intent labels;
- an engine and declared location has no valid runs, so no band exists;
- the competitor set is not two to four brands;
- the template lacks a rule slot, or any slot is empty.
"""

import csv
import datetime
import json
import os
import re
from collections import Counter, defaultdict

import bands
import counter
from config import INTENTS

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "report_template.md")

RULE_SLOTS = {
    "rule1_range_and_sample": "Rule 1: every rate with its count and a 95% band",
    "rule2_split": "Rule 2: split by engine and declared location, no pooled headline",
    "rule3_prompt_list": "Rule 3: prompt list attached, with intent labels",
    "rule3_share_of_voice": "Rule 3: share of voice states prompts, engines, location, runs and denominator",
    "rule4_dates": "Rule 4: date of this measurement",
    "rule4_next": "Rule 4: date of the next measurement",
    "rule5_pilot": "Rule 5: first sample marked as a pilot where it is one",
    "rule6_directional": "Rule 6: directional wording where bands are wide",
    "limits": "All rules: limits section present",
}


class ReportRefused(Exception):
    def __init__(self, reasons):
        self.reasons = list(reasons)
        super().__init__("report refused:\n  - " + "\n  - ".join(self.reasons))


# ---------------------------------------------------------------- formatting

def rate_text(k, n):
    """'34% (120 of 349), band 30 to 40', or 'not observed in n runs' for zero."""
    lo, hi = bands.band_pct(k, n)
    if k == 0:
        return "not observed in %d runs (band %d to %d)" % (n, lo, hi)
    return "%d%% (%d of %d), band %d to %d" % (bands.pct(k / n), k, n, lo, hi)


def share(k, n):
    return "%d%%" % bands.pct(k / n) if n else "n/a"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def add_weeks(date_text, weeks):
    d = datetime.date.fromisoformat(date_text)
    return (d + datetime.timedelta(weeks=weeks)).isoformat()


# ---------------------------------------------------------------- computing

class Data:
    def __init__(self, m):
        self.m = m
        self.manifest = m.manifest
        self.protocol = m.protocol
        self.plan = m.plan()
        self.records = m.records()
        self.changes = m.changes()
        self.deviations = m.deviations()
        self.rows, self.applied = counter.code_all(self.records, self.protocol, self.changes)
        self.engines = [e for e in self.protocol["engines"]]
        self.engine_label = {e["id"]: e.get("label") or e["id"] for e in self.engines}
        self.locations = [loc["label"] for loc in self.protocol["locations"]]
        self.prompts = self.protocol["prompts"]
        self.prompt_by_id = {p["id"]: p for p in self.prompts}
        self.client = self.protocol["brand"]["name"]
        self.competitors = [c["name"] for c in self.protocol["competitors"]]
        self.others = [o["name"] for o in self.protocol.get("other_brands") or []]
        agreement_path = m.path("agreement.json")
        self.agreement = None
        if os.path.exists(agreement_path):
            with open(agreement_path, "r", encoding="utf-8") as fh:
                self.agreement = json.load(fh)

    def head(self):
        """Valid unbranded rows: the headline population."""
        return [r for r in self.rows if r["valid"] and not r["branded"]]

    def cell(self, engine, location, rows=None):
        rows = self.head() if rows is None else rows
        return [r for r in rows if r["engine"] == engine and r["location"] == location]

    def pairs(self):
        for loc in self.locations:
            for e in self.engines:
                yield e["id"], loc


def refusals(d):
    reasons = []
    if not d.records:
        reasons.append("the run log is empty")
        return reasons
    mid, h = d.manifest["measurement_id"], d.manifest["config_hash"]
    other = {(r.get("measurement_id"), r.get("config_hash")) for r in d.records} - {(mid, h)}
    if other:
        reasons.append("the run log holds rows of another measurement or config hash: %s" % sorted(map(str, other)))
    logged = {r["run"] for r in d.records}
    stopped = {x["engine"] for x in d.deviations if x.get("kind") == "engine_stopped"}
    missing = [p for p in d.plan if p["run"] not in logged]
    unexplained = [p for p in missing if p["engine"] not in stopped]
    if unexplained:
        reasons.append("the measurement is incomplete: %d planned runs are not in the log yet" % len(unexplained))
    for p in d.prompts:
        if p.get("intent") not in INTENTS:
            reasons.append("prompt %s has no intent label" % p.get("id"))
    if not (2 <= len(d.competitors) <= 4):
        reasons.append("the competitor set must hold two to four brands")
    for eid, loc in d.pairs():
        if not d.cell(eid, loc):
            reasons.append("%s at %s has no valid runs, so no rate or band can be given"
                           % (d.engine_label[eid], loc))
    return reasons


# ---------------------------------------------------------------- slots

def slot_title(d):
    return "# RSVP report: %s" % d.client


def slot_banner(d):
    if d.protocol.get("illustrative"):
        return ("**Illustrative.** Every brand, engine, answer and number in this report is made up. "
                "It was produced by the dry run on canned answers to show the format. It is not a "
                "measurement of any real product or engine.")
    return "Computed from the run log of this measurement. Every rate is for the prompt list in section 1 only."


def run_dates(d):
    dates = sorted(r["sent_at"][:10] for r in d.records if r.get("sent_at"))
    return dates[0], dates[-1]


def slot_rule4_dates(d):
    first, last = run_dates(d)
    days = len({r["sent_at"][:10] for r in d.records})
    return "Measured %s to %s, %d day%s with runs (dates of the calls, UTC)." % (
        first, last, days, "" if days == 1 else "s")


def slot_rule4_next(d):
    _, last = run_dates(d)
    w = d.protocol["remeasure_weeks"]
    return ("**Next measurement: %s**, %d weeks after the last run, with the same inputs "
            "(prompt list, alias list, competitor set, engines, declared location and how it is passed). "
            "Measure again sooner if you learn that an engine changed. These results hold for the dates "
            "above only." % (add_weeks(last, w), w))


def slot_inputs(d):
    p = d.protocol
    b = p["brand"]
    lines = []
    lines.append("- **Brand:** %s (%s). Aliases: %s. Exclusions: %s." % (
        b["name"], b["domain"], ", ".join(b.get("aliases") or []) or "none",
        ", ".join(b.get("exclusions") or []) or "none"))
    lines.append("- **Named competitors (%d, fixed before the first run):** %s." % (
        len(d.competitors), ", ".join("%s (%s)" % (c["name"], c.get("domain") or "no domain")
                                     for c in p["competitors"])))
    if d.others:
        lines.append("- **Other brands tracked for order only:** %s." % ", ".join(d.others))
    lines.append("- **Declared locations:** %s. **Network location:** %s." % (
        "; ".join(d.locations), p["network_location"]))
    lines.append("- **Engines:**")
    for e in d.engines:
        how = "the engine's location setting" if e["location_method"] == "setting" else \
            "a sentence at the start of the prompt (\"%s\")" % p["location_sentence"]
        lines.append("  - %s: adapter %s, model %s, mode %s, interface %s. Location passed by %s." % (
            d.engine_label[e["id"]], e["adapter"], e.get("model") or "not shown", e["mode"],
            e["interface"], how))
    planned = len(d.plan)
    valid = sum(1 for r in d.rows if r["valid"])
    failed = sum(1 for r in d.rows if not r["valid"])
    not_run = planned - len(d.records)
    unbranded = [x for x in d.prompts if not x["branded"]]
    lines.append("- **Runs:** %d per prompt per engine and location, over %d scheduled days. "
                 "%d planned, %d valid, %d failed and excluded%s." % (
                     p["runs_per_prompt"], p["schedule_days"], planned, valid, failed,
                     ", %d not run (see deviations)" % not_run if not_run else ""))
    lines.append("- **Prompts:** %d unbranded (%s)%s." % (
        len(unbranded),
        ", ".join("%d %s" % (sum(1 for x in unbranded if x["intent"] == i), i) for i in INTENTS),
        "; %d branded, reported apart" % (len(d.prompts) - len(unbranded)) if len(unbranded) < len(d.prompts) else ""))
    return "\n".join(lines)


def competitor_named(d, prompt):
    brands = counter.brand_table(d.protocol)[1:1 + len(d.competitors)]
    return any(counter.text_names_any(prompt["text"], b["aliases"], b["exclusions"]) for b in brands)


def slot_prompt_list(d):
    rows = []
    for x in d.prompts:
        flags = []
        if x["branded"]:
            flags.append("branded")
        if competitor_named(d, x):
            flags.append("competitor-named")
        if x.get("eligible") is True:
            flags.append("eligible")
        if x.get("eligible") is False:
            flags.append("ineligible")
        rows.append((x["id"], x["need"], x["intent"], ", ".join(flags) or "", x["text"].replace("|", "/")))
    return table(("ID", "Need", "Intent", "Flags", "Prompt"), rows)


def slot_rule2_split(d):
    return ("Every figure is split by engine and by declared location. No figure is pooled across "
            "engines or locations. Engines: %s. Declared locations: %s." % (
                ", ".join(d.engine_label[e["id"]] for e in d.engines), "; ".join(d.locations)))


def headline_figures(d):
    out = []
    for eid, loc in d.pairs():
        c = d.cell(eid, loc)
        n = len(c)
        out.append({
            "engine": eid, "location": loc, "n": n,
            "visible": sum(1 for r in c if r["mention"] or r["cited"]),
            "mention": sum(1 for r in c if r["mention"]),
            "cited": sum(1 for r in c if r["cited"]),
            "ghost": sum(1 for r in c if r["ghost"]),
        })
    return out


def wide(k, n, limit):
    return bands.band_width_points(k, n) > limit


def slot_rule1(d, figs):
    limit = d.protocol["directional_band_width"]
    rows = []
    for f in figs:
        marks = [name for name, k in (("visibility", f["visible"]), ("mention", f["mention"]),
                                      ("citation", f["cited"])) if wide(k, f["n"], limit)]
        rows.append((d.engine_label[f["engine"]], f["location"], f["n"],
                     rate_text(f["visible"], f["n"]), rate_text(f["mention"], f["n"]),
                     rate_text(f["cited"], f["n"]),
                     "wide: " + ", ".join(marks) if marks else "within %s points" % _num(limit)))
    note = ("Visibility rate: valid runs with a mention or a citation, divided by valid runs. "
            "Failed runs are left out of every denominator. Runs with no citations stay in. "
            "Bands are 95% Wilson intervals, in percent.")
    return table(("Engine", "Declared location", "Valid runs", "Visibility rate", "Mention rate",
                  "Citation rate", "Band width"), rows) + "\n\n" + note


def _num(x):
    return ("%g" % x)


def slot_by_intent(d):
    rows = []
    for eid, loc in d.pairs():
        c = d.cell(eid, loc)
        for intent in INTENTS:
            ci = [r for r in c if r["intent"] == intent]
            if not ci:
                continue
            k = sum(1 for r in ci if r["mention"])
            rows.append((d.engine_label[eid], loc, intent, rate_text(k, len(ci))))
    return table(("Engine", "Declared location", "Intent", "Mention rate"), rows) + \
        "\n\nRates are not weighted by any assumed share of traffic. Each intent is reported on its own."


def slot_citation(d, figs):
    rows = []
    extra = []
    for f in figs:
        c = d.cell(f["engine"], f["location"])
        both = sum(1 for r in c if r["mention"] and r["cited"])
        m_only = sum(1 for r in c if r["mention"] and not r["cited"])
        neither = sum(1 for r in c if not r["mention"] and not r["cited"])
        no_cit = sum(1 for r in c if not r["domains"])
        rows.append((d.engine_label[f["engine"]], f["location"], f["n"], both, m_only, f["ghost"],
                     neither, no_cit))
        dom = Counter(dm for r in c for dm in r["domains"])
        top = ", ".join("%s (%d)" % (k, v) for k, v in sorted(dom.items(), key=lambda kv: (-kv[1], kv[0]))[:5])
        extra.append("- %s, %s: most cited domains, in runs out of %d valid: %s." % (
            d.engine_label[f["engine"]], f["location"], f["n"], top or "none"))
    return (table(("Engine", "Declared location", "Valid runs", "Mentioned and cited",
                   "Mentioned, not cited", "Cited, not mentioned (ghost)", "Neither",
                   "Runs with no citations"), rows)
            + "\n\nCitation matches the brand's registrable domain, subdomains included, after tracking "
              "parameters are stripped and redirects resolved. A ghost citation counts toward the citation "
              "and visibility rates, not the mention rate. A citation shows presence among the sources, "
              "not endorsement.\n\n" + "\n".join(extra))


def slot_position(d):
    rows = []
    for eid, loc in d.pairs():
        c = [r for r in d.cell(eid, loc) if r["mention"]]
        k = len(c)
        cnt = Counter(r["pos_band"] for r in c)
        if sum(cnt.values()) != k:
            raise ReportRefused(["position bands do not add up to the mention count for %s" % eid])
        if k == 0:
            rows.append((d.engine_label[eid], loc, 0, "position not defined: no mentions", "", ""))
            continue
        rows.append((d.engine_label[eid], loc, k) + tuple(
            "%d (%s)" % (cnt[b], share(cnt[b], k)) for b in counter.POSITION_BANDS))
    return (table(("Engine", "Declared location", "Mentions", "1st named", "2nd or 3rd", "4th or later"), rows)
            + "\n\nCounted only for runs with a mention. Each mention falls in exactly one band, so the three "
              "counts sum to the mentions. Text order stands in for prominence; it does not measure attention.")


def slot_share_of_voice(d):
    lines = []
    unbranded = [x["id"] for x in d.prompts if not x["branded"]]
    rows = []
    brand_rows = []
    for eid, loc in d.pairs():
        c = d.cell(eid, loc)
        client = sum(1 for r in c if r["mention"])
        comp = sum(len(r["comp"]) for r in c)
        denom = client + comp
        sov = ("%.1f%% (%d of %d brand mentions)" % (100.0 * client / denom, client, denom)
               if denom else "not defined: no brand mentions counted")
        rows.append((d.engine_label[eid], loc, client, comp, sov))
        per = [sum(1 for r in c if d.client in r["brands"])] + \
              [sum(1 for r in c if name in r["comp"]) for name in d.competitors]
        brand_rows.append((d.engine_label[eid], loc) + tuple("%d (%s)" % (k, share(k, len(c))) for k in per))
    lines.append("Share of voice is client mentions divided by client plus named-competitor mentions, over "
                 "the same runs, one count per brand per run. It is for the %d unbranded prompts listed in "
                 "section 1 (%s), the engines and declared locations shown, at %d runs per prompt. It is "
                 "descriptive: counts only, no band. It is not market share."
                 % (len(unbranded), ", ".join(unbranded), d.protocol["runs_per_prompt"]))
    lines.append("")
    lines.append(table(("Engine", "Declared location", "Client mentions",
                        "Named-competitor mentions (%d named)" % len(d.competitors), "Share of voice"), rows))
    lines.append("")
    lines.append("Runs naming each brand, with the share of valid runs:")
    lines.append("")
    lines.append(table(("Engine", "Declared location", d.client) + tuple(d.competitors), brand_rows))
    if d.others:
        lines.append("")
        parts = []
        for eid, loc in d.pairs():
            c = d.cell(eid, loc)
            cnt = Counter(b for r in c for b in r["brands"] if b in d.others)
            parts.append("%s, %s: %s" % (d.engine_label[eid], loc, ", ".join(
                "%s %d" % (k, v) for k, v in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"))
        lines.append("Other brands named (not in share of voice; found from the tracked list only, so an "
                     "approximation): " + "; ".join(parts) + ".")
    return "\n".join(lines)


def cells(d, eid, loc):
    out = []
    for x in d.prompts:
        if x["branded"]:
            continue
        rs = [r for r in d.cell(eid, loc) if r["prompt"] == x["id"]]
        out.append((x, rs))
    return out


def slot_spread(d):
    rows = []
    words = []
    for eid, loc in d.pairs():
        cl = Counter()
        bj, dj = [], []
        rot = Counter()
        order_shifts = False
        cs = cells(d, eid, loc)
        for x, rs in cs:
            n = len(rs)
            if not n:
                continue
            cl[bands.cell_class(sum(1 for r in rs if r["mention"]), n)] += 1
            b = bands.mean_pairwise_jaccard([r["brands"] for r in rs])
            if b is not None:
                bj.append(b)
            dd = bands.mean_pairwise_jaccard([r["domains"] for r in rs])
            if dd is not None:
                dj.append(dd)
            for name in d.competitors:
                if bands.rotates(sum(1 for r in rs if name in r["comp"]), n):
                    rot[name] += 1
            if len({r["pos_band"] for r in rs if r["mention"]}) > 1:
                order_shifts = True
        classified = sum(cl.values())
        rows.append((d.engine_label[eid], loc) + tuple(cl[c] for c in bands.CELL_CLASSES) + (
            "%.2f" % (sum(bj) / len(bj)) if bj else "n/a",
            "%.2f" % (sum(dj) / len(dj)) if dj else "n/a"))
        desc = []
        if classified and cl["flipping"] * 2 > classified:
            desc.append("wide swings between runs (%d of %d cells flipping)" % (cl["flipping"], classified))
        if rot:
            desc.append("%d of %d named competitors rotate in and out (%s)" % (
                len(rot), len(d.competitors),
                ", ".join("%s in %d of %d cells" % (k, v, classified) for k, v in sorted(rot.items()))))
        else:
            desc.append("stable list of named competitors (none rotates in any cell)")
        if order_shifts:
            desc.append("the brand's position band shifts between runs of the same prompt")
        words.append("- **%s, %s:** %s." % (d.engine_label[eid], loc, "; ".join(desc)))
    out = [table(("Engine", "Declared location") + tuple(c.capitalize() for c in bands.CELL_CLASSES)
                 + ("Brand overlap", "Domain overlap"), rows)]
    out.append("")
    out.append("A cell is one prompt on one engine and declared location, classed by its mention rate: never "
               "0%, rarely under 30%, flipping 30% to 70%, mostly over 70% and under 100%, always 100%. "
               "With few runs a cell's class is itself noisy. Overlap is the mean Jaccard index over every "
               "pair of valid runs in a cell (pairs where both sets are empty are skipped), then the mean "
               "over cells; 1.00 means identical sets. A competitor rotates in a cell when it appears in "
               "more than 10% and fewer than 90% of the cell's valid runs.")
    out.append("")
    out.extend(words)
    out.append("")
    out.append("**Day by day (mention rate):**")
    out.append("")
    days = sorted({r["date"] for r in d.head()})
    drows = []
    for day in days:
        row = [day]
        for eid, loc in d.pairs():
            c = [r for r in d.cell(eid, loc) if r["date"] == day]
            k = sum(1 for r in c if r["mention"])
            row.append(rate_text(k, len(c)) if c else "no runs")
        drows.append(row)
    out.append(table(["Date"] + ["%s, %s" % (d.engine_label[e], l) for e, l in d.pairs()], drows))
    out.append("")
    out.append("Each day holds fewer runs than the whole measurement, so each day's band is wider. "
               "A change seen on a single day is noise, not a result.")
    return "\n".join(out)


def slot_reading(d, figs):
    out = []
    for loc in d.locations:
        fl = [f for f in figs if f["location"] == loc]
        fl.sort(key=lambda f: -f["visible"] / f["n"])
        pairs = []
        for i in range(len(fl)):
            for j in range(i + 1, len(fl)):
                a, b = fl[i], fl[j]
                la, lb = d.engine_label[a["engine"]], d.engine_label[b["engine"]]
                if bands.bands_overlap((a["visible"], a["n"]), (b["visible"], b["n"])):
                    pairs.append("%s and %s: bands overlap, no difference shown" % (la, lb))
                else:
                    pairs.append("%s above %s: bands do not overlap" % (la, lb))
        if pairs:
            out.append("- **Engines, visibility rate, %s, on this prompt list and these dates:** %s." % (
                loc, "; ".join(pairs)))
    lows = []
    for eid, loc in d.pairs():
        c = d.cell(eid, loc)
        rates = {}
        for intent in INTENTS:
            ci = [r for r in c if r["intent"] == intent]
            if ci:
                rates[intent] = sum(1 for r in ci if r["mention"]) / len(ci)
        if rates:
            lows.append((eid, loc, min(rates, key=lambda i: (rates[i], INTENTS.index(i)))))
    if lows:
        common = Counter(x[2] for x in lows).most_common(1)[0]
        out.append("- **Intent:** the lowest mention rate is on %s prompts for %d of %d engine and location "
                   "pairs. A low rate on prompts that do not call for a product is not by itself a problem."
                   % (common[0], common[1], len(lows)))
    ghost = ["%s, %s: %d ghost citations next to %d mentions" % (
        d.engine_label[f["engine"]], f["location"], f["ghost"], f["mention"]) for f in figs]
    out.append("- **Ghost citations:** " + "; ".join(ghost) + ".")
    drift = []
    for eid, loc in d.pairs():
        days = sorted({r["date"] for r in d.cell(eid, loc)})
        if len(days) < 2:
            continue
        first = [r for r in d.cell(eid, loc) if r["date"] == days[0]]
        last = [r for r in d.cell(eid, loc) if r["date"] == days[-1]]
        kf, kl = sum(1 for r in first if r["mention"]), sum(1 for r in last if r["mention"])
        verdict = ("bands overlap, no change shown" if bands.bands_overlap((kf, len(first)), (kl, len(last)))
                   else "bands do not overlap, worth re-measuring sooner")
        drift.append("%s, %s: %s on %s, %s on %s; %s" % (
            d.engine_label[eid], loc, share(kf, len(first)), days[0], share(kl, len(last)), days[-1], verdict))
    if drift:
        out.append("- **Drift (mention rate, first and last day):** " + "; ".join(drift) +
                   ". A single day proves nothing; a move that holds across the days is a reason to "
                   "measure again sooner.")
    out.append("- RSVP measures and does not explain. Any suspected cause is a hypothesis: write it down, "
               "change one thing, and re-measure with the same inputs.")
    return "\n".join(out)


def pilot_reasons(d):
    p = d.protocol
    reasons = []
    if p["runs_per_prompt"] <= p["pilot_threshold"]:
        reasons.append("%d runs per prompt is at or below the pilot threshold of %d"
                       % (p["runs_per_prompt"], p["pilot_threshold"]))
    if p["first_measurement"]:
        reasons.append("it is the first measurement under this protocol")
    return reasons


def slot_rule5(d):
    reasons = pilot_reasons(d)
    if reasons:
        return ("**PILOT.** This measurement is a pilot: %s. It is kept small on purpose, because cost grows "
                "with prompts times engines times runs times locations. Add runs where a result is close "
                "to a decision." % "; ".join(reasons))
    return ("Not a pilot: %d runs per prompt is above the pilot threshold of %d, and the config states that "
            "this is not the first measurement under this protocol."
            % (d.protocol["runs_per_prompt"], d.protocol["pilot_threshold"]))


def slot_rule6(d, figs):
    limit = d.protocol["directional_band_width"]
    wide_cells = ["%s, %s" % (d.engine_label[f["engine"]], f["location"]) for f in figs
                  if any(wide(k, f["n"], limit) for k in (f["visible"], f["mention"], f["cited"]))]
    reasons = []
    if pilot_reasons(d):
        reasons.append("the sample is a pilot")
    if wide_cells:
        reasons.append("a headline band is wider than %s points for %s" % (_num(limit), "; ".join(wide_cells)))
    if reasons:
        return ("**DIRECTIONAL.** Read every number in this report as direction only, not as a firm level: "
                "%s. With few runs the bands are wide." % "; ".join(reasons))
    return ("Every headline band is at most %s points wide and the sample is not a pilot, so the headline "
            "is not marked directional. Intent-level, day-level and prompt-level figures rest on fewer runs "
            "and have wider bands." % _num(limit))


def slot_limits(d):
    items = [
        "Answers fetched through an API match what the engine's own web page cites only in part, so this "
        "report speaks about brands and domains, never about a particular page.",
        "The location was stated to each engine, not observed. Engines differ in whether they use the stated "
        "location or the network the call came from; the network location is given in section 1.",
        "Few runs mean wide bands. The band formula assumes independent runs; runs of different prompts "
        "share a brand and a market, so the true uncertainty is a little larger than shown.",
        "Each band covers run-to-run noise for this prompt list only. It does not cover the choice of "
        "prompts or drift after these dates.",
        "This report gives no reason why the brand is or is not named, no forecast of what any change "
        "would do, and no figure for traffic, clicks, revenue, tone or accuracy.",
    ]
    no_search = sum(1 for r in d.head() if not r["domains"])
    items.append("%d of %d valid unbranded runs showed no citations; they are valid outcomes and stay in "
                 "every denominator." % (no_search, len(d.head())))
    served = defaultdict(set)
    for r in d.rows:
        if r["valid"] and r.get("served_model"):
            served[r["engine"]].add(r["served_model"])
    changed = ["%s served %s" % (d.engine_label[e], ", ".join(sorted(v))) for e, v in served.items() if len(v) > 1]
    if changed:
        items.append("Serving model changed during the measurement: %s." % "; ".join(changed))
    if any(x["engine"] for x in d.deviations if x.get("kind") == "engine_stopped"):
        items.append("An engine was stopped during the measurement; see the method note.")
    return "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(items))


def slot_method_note(d):
    out = []
    p = d.protocol
    out.append("- **Measurement ID:** %s. **Config hash:** %s. **Code:** %s. **Method:** %s." % (
        d.manifest["measurement_id"], d.manifest["config_hash"][:16], d.manifest["code_version"],
        d.manifest["method_version"]))
    if d.manifest.get("previous_measurement"):
        out.append("- **Previous measurement under this protocol ID:** %s. Changed: %s. Not comparable "
                   "where the changed inputs matter." % (d.manifest["previous_measurement"],
                                                        ", ".join(d.manifest.get("changed_detail") or
                                                                  d.manifest.get("changed_sections") or [])))
    statuses = Counter(r["status"] for r in d.rows)
    out.append("- **Run status:** " + ", ".join("%s %d" % (s, statuses[s]) for s in counter.ALL_STATUSES) +
               ". Error, empty and timeout are failed runs and are excluded. A refusal in text is a valid run "
               "with no mention.")
    retried = sum(1 for r in d.records if r.get("attempt_errors"))
    out.append("- **Retries:** %d runs needed more than one attempt (technical failures only, at most three "
               "attempts)." % retried)
    bat = []
    for eid, loc in d.pairs():
        rates = []
        for x, rs in cells(d, eid, loc):
            if rs:
                rates.append(sum(1 for r in rs if r["mention"]) / len(rs))
        c = d.cell(eid, loc)
        pooled = sum(1 for r in c if r["mention"]) / len(c)
        bat.append("%s, %s: battery %.1f%%, pooled %.1f%%" % (
            d.engine_label[eid], loc, 100 * sum(rates) / len(rates), 100 * pooled))
    out.append("- **Battery mention rate** (mean of per-prompt rates, equal weight per prompt) against the "
               "pooled rate used in the headline: " + "; ".join(bat) + ".")
    elig = [x for x in d.prompts if not x["branded"] and x.get("eligible") is not None]
    if elig:
        parts = []
        for eid, loc in d.pairs():
            for flag, name in ((True, "eligible"), (False, "ineligible")):
                rs = [r for r in d.cell(eid, loc) if r["eligible"] is flag]
                if rs:
                    parts.append("%s, %s, %s: %s" % (d.engine_label[eid], loc, name,
                                                     rate_text(sum(1 for r in rs if r["mention"]), len(rs))))
        out.append("- **Eligibility** (coded before the first run, optional): mention rate " + "; ".join(parts) +
                   ". A low rate on an eligible prompt is worth a closer look; it does not show the engine is wrong.")
    branded = [x for x in d.prompts if x["branded"]]
    if branded:
        parts = []
        for eid, loc in d.pairs():
            rs = [r for r in d.rows if r["valid"] and r["branded"] and r["engine"] == eid and r["location"] == loc]
            if rs:
                parts.append("%s, %s: %s" % (d.engine_label[eid], loc,
                                             rate_text(sum(1 for r in rs if r["mention"]), len(rs))))
        out.append("- **Branded block** (%s; measures whether the engine knows the brand, kept out of every "
                   "figure above): mention rate %s." % (", ".join(x["id"] for x in branded), "; ".join(parts)))
    if d.agreement:
        parts = []
        low = []
        for field, v in sorted(d.agreement["fields"].items()):
            parts.append("%s %s (%d of %d)" % (field, share(v["agree"], v["n"]), v["agree"], v["n"]))
            if v["n"] and v["agree"] / v["n"] < 0.90:
                low.append(field)
        out.append("- **Second-analyst recode** of %d valid runs: agreement %s.%s" % (
            d.agreement["sample_size"], ", ".join(parts),
            " Below 90%% on %s: rewrite the coding rules and recode the log before this report is used."
            % ", ".join(low) if low else ""))
    else:
        out.append("- **Second-analyst recode:** not done yet. Write the sample with `python3 rsvp.py "
                   "recode-sample`, have a second analyst fill it without seeing the coding, then run "
                   "`python3 rsvp.py agreement`. Report agreement before release.")
    out.append("- **Corrections applied from the change list:** %d (originals kept in the run log)." % len(d.applied))
    if d.deviations:
        for x in d.deviations:
            out.append("- **Deviation:** %s %s at %s: %s." % (x.get("kind"), x.get("engine", ""),
                                                            x.get("at", ""), x.get("reason", "")))
    else:
        out.append("- **Deviations:** none logged.")
    return "\n".join(out)


def slot_prompt_appendix(d):
    out = []
    pairs = list(d.pairs())
    rows = []
    for x in d.prompts:
        if x["branded"]:
            continue
        row = [x["id"], x["need"], x["intent"]]
        for eid, loc in pairs:
            rs = [r for r in d.cell(eid, loc) if r["prompt"] == x["id"]]
            row.append("%d/%d" % (sum(1 for r in rs if r["mention"]), len(rs)))
        rows.append(row)
    out.append(table(["Prompt", "Need", "Intent"] + ["%s, %s" % (d.engine_label[e], l) for e, l in pairs], rows))
    out.append("")
    out.append("Mentions out of valid runs. Counts only, with no bands, listed in prompt order and not ranked: "
               "each cell holds too few runs for a band that could separate prompts.")
    needs = defaultdict(list)
    for x in d.prompts:
        if not x["branded"]:
            needs[x["need"]].append(x["id"])
    if any(len(v) > 1 for v in needs.values()):
        nrows = []
        for need, ids in needs.items():
            row = [need, ", ".join(ids)]
            for eid, loc in pairs:
                rs = [r for r in d.cell(eid, loc) if r["prompt"] in ids]
                row.append("%d/%d" % (sum(1 for r in rs if r["mention"]), len(rs)))
            nrows.append(row)
        out.append("")
        out.append("**By need.** Paraphrases of one buyer need share a need ID and are read together, "
                   "not as separate evidence:")
        out.append("")
        out.append(table(["Need", "Prompts"] + ["%s, %s" % (d.engine_label[e], l) for e, l in pairs], nrows))
    return "\n".join(out)


def slot_rule_check(slots):
    rows = [(label, "filled" if slots.get(name, "").strip() else "EMPTY") for name, label in RULE_SLOTS.items()]
    return table(("Check", "Slot"), rows)


# ---------------------------------------------------------------- rendering

def render(template_text, slots):
    names = re.findall(r"\{\{(\w+)\}\}", template_text)
    problems = []
    for rule in RULE_SLOTS:
        if rule not in names:
            problems.append("the template has no slot for %s" % RULE_SLOTS[rule])
    for name in names:
        if not str(slots.get(name, "")).strip():
            problems.append("slot %s is empty" % name)
    if problems:
        raise ReportRefused(problems)
    text = re.sub(r"\{\{(\w+)\}\}", lambda mt: str(slots[mt.group(1)]), template_text)
    if "\u2014" in text:
        text = text.replace("\u2014", ", ")
    return text.rstrip() + "\n"


def build_slots(d):
    figs = headline_figures(d)
    slots = {
        "title": slot_title(d),
        "banner": slot_banner(d),
        "measurement_id": d.manifest["measurement_id"],
        "rule4_dates": slot_rule4_dates(d),
        "inputs": slot_inputs(d),
        "rule3_prompt_list": slot_prompt_list(d),
        "rule2_split": slot_rule2_split(d),
        "rule1_range_and_sample": slot_rule1(d, figs),
        "by_intent": slot_by_intent(d),
        "citation": slot_citation(d, figs),
        "position": slot_position(d),
        "rule3_share_of_voice": slot_share_of_voice(d),
        "spread": slot_spread(d),
        "reading": slot_reading(d, figs),
        "rule5_pilot": slot_rule5(d),
        "rule6_directional": slot_rule6(d, figs),
        "limits": slot_limits(d),
        "rule4_next": slot_rule4_next(d),
        "method_note": slot_method_note(d),
        "prompt_appendix": slot_prompt_appendix(d),
    }
    slots["rule_check"] = slot_rule_check(slots)
    return slots


CODED_COLUMNS = ("run", "date", "engine", "prompt", "need", "intent", "branded", "location", "status",
                 "valid", "brands", "mention", "cited", "ghost", "pos", "pos_band", "comp", "domains")


def write_coded_log(d, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CODED_COLUMNS)
        for r in sorted(d.rows, key=lambda r: r["run"]):
            w.writerow([";".join(r[c]) if isinstance(r[c], list) else
                        (int(r[c]) if isinstance(r[c], bool) else ("" if r[c] is None else r[c]))
                        for c in CODED_COLUMNS])


def build_report(m, template_path=TEMPLATE):
    d = Data(m)
    reasons = refusals(d)
    if reasons:
        raise ReportRefused(reasons)
    with open(template_path, "r", encoding="utf-8") as fh:
        template_text = fh.read()
    text = render(template_text, build_slots(d))
    write_coded_log(d, m.path("coded_runlog.csv"))
    with open(m.path("report.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text
