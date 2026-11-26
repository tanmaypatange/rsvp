import copy
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import tests  # noqa: F401
from tests.helpers import BASE, Workspace, canned_all, ok
import reporter
import counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MIXED = [
    ok("1. Acme Books\n2. Birch Ledger", ["https://acmebooks.example/a"]),
    ok("Birch Ledger, Cedar Accounts, Dune Pay and Acme.", ["https://x.example"]),
    ok("Birch Ledger only.", ["https://acmebooks.example/b?utm_source=a"]),
    ok("Cedar Accounts and Birch Ledger, then Acme Books."),
]


class Refusals(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def assertRefused(self, m, text):
        with self.assertRaises(reporter.ReportRefused) as ctx:
            reporter.build_report(m)
        self.assertTrue(any(text in r for r in ctx.exception.reasons), ctx.exception.reasons)
        self.assertFalse(os.path.exists(m.path("report.md")))

    def test_refuses_an_empty_slot(self):
        cfg, m = self.ws.run(canned_all(MIXED))
        d = reporter.Data(m)
        slots = reporter.build_slots(d)
        slots["rule5_pilot"] = "  "
        with open(reporter.TEMPLATE) as fh:
            tpl = fh.read()
        with self.assertRaises(reporter.ReportRefused) as ctx:
            reporter.render(tpl, slots)
        self.assertIn("slot rule5_pilot is empty", ctx.exception.reasons)

    def test_refuses_a_template_without_a_rule_slot(self):
        cfg, m = self.ws.run(canned_all(MIXED))
        with open(reporter.TEMPLATE) as fh:
            tpl = fh.read().replace("{{rule6_directional}}", "")
        path = os.path.join(self.ws.dir, "tpl.md")
        with open(path, "w") as fh:
            fh.write(tpl)
        with self.assertRaises(reporter.ReportRefused) as ctx:
            reporter.build_report(m, template_path=path)
        self.assertTrue(any("no slot for Rule 6" in r for r in ctx.exception.reasons))

    def test_refuses_when_an_engine_has_no_valid_runs(self):
        cfg, m = self.ws.run(canned_all([{"fail_attempts": 3, "fail_status": "timeout"}]))
        self.assertRefused(m, "has no valid runs")

    def test_refuses_an_incomplete_measurement(self):
        cfg = self.ws.config(canned_all(MIXED))
        import runner
        m = runner.run_measurement(cfg, clock=runner.SimulatedClock("2026-11-02"),
                                   resolver=runner.RedirectResolver(enabled=False), log=lambda *a: None)
        self.assertRefused(m, "incomplete")

    def test_refuses_rows_of_another_measurement(self):
        cfg, m = self.ws.run(canned_all(MIXED))
        with open(m.path("runlog.jsonl")) as fh:
            first = fh.readline()
        with open(m.path("runlog.jsonl"), "a") as fh:
            fh.write(first.replace(m.manifest["config_hash"], "0" * 64))
        self.assertRefused(m, "another measurement")

    def test_refuses_an_empty_log(self):
        cfg = self.ws.config(canned_all(MIXED))
        import runlog
        import runner
        m, _, _ = runlog.start_or_resume(cfg, runner.schedule(runner.expand(cfg), 1))
        self.assertRefused(m, "empty")


class Figures(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def report(self, canned, **kw):
        cfg, m = self.ws.run(canned, **kw)
        return reporter.build_report(m), m

    def test_failed_runs_left_out_of_the_denominator(self):
        answers = [ok("Acme Books"), {"fail_attempts": 3, "fail_status": "error"}, ok("Birch Ledger"), ok("x")]
        text, m = self.report(canned_all(answers))
        # Each prompt: 4 runs, 1 failed, so 3 valid per prompt and 6 valid per engine.
        self.assertIn("| Engine One | United States | 6 | 33% (2 of 6), band 10 to 70", text)
        self.assertIn("6 valid, 2 failed and excluded", text)

    def test_headline_has_counts_and_bands(self):
        text, m = self.report(canned_all(MIXED))
        row = [l for l in text.splitlines() if l.startswith("| Engine One | United States | 8 |")][0]
        # visible: runs 1, 2, 3, 4 all visible -> 8 of 8; mention: 1, 2, 4 -> 6 of 8; cited: 1, 3 -> 4 of 8
        self.assertIn("100% (8 of 8), band 68 to 100", row)
        self.assertIn("75% (6 of 8), band 41 to 93", row)
        self.assertIn("50% (4 of 8), band 22 to 78", row)

    def test_zero_count_is_written_as_not_observed(self):
        text, m = self.report(canned_all([ok("Birch Ledger only.")]))
        self.assertIn("not observed in 8 runs (band 0 to 32)", text)
        self.assertNotIn("never appears", text.lower())

    def test_position_bands_add_up_to_mentions(self):
        text, m = self.report(canned_all(MIXED))
        # Per prompt: run 1 first named, run 2 fourth, run 4 third.
        self.assertIn("| Engine One | United States | 6 | 2 (33%) | 2 (33%) | 2 (33%) |", text)

    def test_share_of_voice_counts_with_denominator_and_no_band(self):
        text, m = self.report(canned_all(MIXED))
        # Client mentions 6; competitor mentions per prompt: Birch in 4 runs, Cedar in 2, so 12 in all.
        self.assertIn("33.3% (6 of 18 brand mentions)", text)
        section = text.split("## 6. Share of voice")[1].split("## 7.")[0]
        self.assertNotIn("band", section.replace("no band", ""))
        self.assertIn("unbranded prompts listed", section)
        self.assertIn("runs per prompt", section)

    def test_pilot_label_and_directional_wording(self):
        text, m = self.report(canned_all(MIXED))
        self.assertIn("**PILOT.**", text)
        self.assertIn("**DIRECTIONAL.**", text)

    def test_not_a_pilot_above_threshold_and_not_first(self):
        text, m = self.report(canned_all(MIXED * 3), runs_per_prompt=12, pilot_threshold=10,
                              first_measurement=False, directional_band_width=100)
        self.assertIn("Not a pilot", text)
        self.assertNotIn("**DIRECTIONAL.**", text)

    def test_directional_when_bands_are_wide_even_if_not_a_pilot(self):
        text, m = self.report(canned_all(MIXED * 3), runs_per_prompt=12, pilot_threshold=10,
                              first_measurement=False, directional_band_width=20)
        self.assertIn("Not a pilot", text)
        self.assertIn("**DIRECTIONAL.**", text)
        self.assertIn("wider than 20 points", text)

    def test_split_by_engine_and_location_no_pooled_row(self):
        engines = [dict(BASE["engines"][0]), dict(BASE["engines"][0], id="e2", label="Engine Two")]
        locs = [{"label": "United States", "country": "US"}, {"label": "Canada", "country": "CA"}]
        text, m = self.report(canned_all(MIXED, engines=("e1", "e2")), engines=engines, locations=locs)
        head = text.split("## 2.")[1].split("## 3.")[0]
        rows = [l for l in head.splitlines() if l.startswith("| Engine")]
        self.assertEqual(len(rows), 1 + 4)   # header plus one row per engine and location
        self.assertNotIn("All engines", text)
        self.assertNotIn("pooled across", head.replace("No figure is pooled across", ""))

    def test_prompt_list_with_intent_labels_attached(self):
        text, m = self.report(canned_all(MIXED))
        self.assertIn("| P1 | N1 | commercial |", text)
        self.assertIn("| P2 | N2 | informational |", text)

    def test_dates_and_next_measurement(self):
        text, m = self.report(canned_all(MIXED))
        self.assertIn("Measured 2026-11-02 to 2026-11-03", text)
        self.assertIn("**Next measurement: 2026-12-01**", text)

    def test_cell_classes_and_overlap(self):
        text, m = self.report(canned_all(MIXED))
        # P1 and P2 both 3 of 4 mentions = 75% = mostly
        self.assertIn("| Engine One | United States | 0 | 0 | 0 | 2 | 0 |", text)

    def test_prompt_counts_have_no_bands(self):
        text, m = self.report(canned_all(MIXED))
        appendix = text.split("## Appendix")[1]
        self.assertNotRegex(appendix.split("Mentions out of")[0], r"band|%")

    def test_no_composite_score_sentiment_or_traffic(self):
        text, m = self.report(canned_all(MIXED))
        lower = text.lower()
        self.assertNotIn("visibility score", lower)
        self.assertNotIn("sentiment", lower)
        self.assertNotRegex(lower, r"traffic: \d|revenue: \d")

    def test_competitor_named_prompt_is_flagged(self):
        prompts = copy.deepcopy(BASE["prompts"])
        prompts[0]["text"] = "Alternatives to Birch Ledger for a bakery"
        text, m = self.report(canned_all(MIXED), prompts=prompts)
        self.assertIn("| P1 | N1 | commercial | competitor-named |", text)

    def test_branded_block_is_kept_out_of_the_headline(self):
        prompts = copy.deepcopy(BASE["prompts"]) + [
            {"id": "P3", "need": "N3", "intent": "commercial", "branded": True, "text": "Is Acme Books any good?"}]
        canned = canned_all(MIXED, prompts=("P1", "P2", "P3"))
        canned["e1"]["P3"] = [ok("Acme Books is good.")]
        text, m = self.report(canned, prompts=prompts)
        self.assertIn("| Engine One | United States | 8 |", text)
        self.assertIn("**Branded block** (P3", text)

    def test_change_list_is_applied_and_counted(self):
        cfg, m = self.ws.run(canned_all(MIXED))
        run = [r for r in m.records() if r["answer_text"] == "Birch Ledger only."][0]["run"]
        m.append_change({"run": run, "field": "pos", "new": 2, "reason": "test"})
        m.append_change({"run": run, "field": "mention", "new": 1, "reason": "test"})
        text = reporter.build_report(m)
        self.assertIn("Corrections applied from the change list:** 2", text)
        self.assertIn("88% (7 of 8)", text)

    def test_no_em_dash_in_any_report(self):
        text, m = self.report(canned_all([ok("Acme Books \u2014 a good pick")]))
        self.assertNotIn("\u2014", text)


class QualityChecks(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def test_recode_sample_and_agreement(self):
        cfg, m = self.ws.run(canned_all(MIXED * 5), runs_per_prompt=20)
        path = os.path.join(self.ws.dir, "sample.csv")
        size = counter.write_recode_sample(m, path)
        self.assertEqual(size, 4)   # 10% of 40 valid runs
        rows, _ = counter.code_all(m.records(), m.protocol)
        by_run = {r["run"]: r for r in rows}
        with open(path) as fh:
            lines = list(csv.reader(fh))
        self.assertNotIn("mention", " ".join(lines[1]).lower().replace("mention (1 or 0)", ""))
        filled = [lines[0]]
        for i, line in enumerate(lines[1:]):
            r = by_run[line[0]]
            mention = int(r["mention"]) if i else 1 - int(r["mention"])   # one deliberate disagreement
            filled.append(line[:6] + [str(mention), str(int(r["cited"])), r["pos_band"] or ""])
        with open(path, "w", newline="") as fh:
            csv.writer(fh).writerows(filled)
        out = counter.agreement(m, path)
        self.assertEqual(out["fields"]["mention"], {"agree": 3, "n": 4})
        self.assertEqual(out["fields"]["cited"], {"agree": 4, "n": 4})
        text = reporter.build_report(m)
        self.assertIn("mention 75% (3 of 4)", text)
        self.assertIn("Below 90% on mention", text)


class EndToEnd(unittest.TestCase):
    def test_dry_run_reproduces_the_committed_sample_report(self):
        out = tempfile.mkdtemp(prefix="rsvp-dry-")
        try:
            res = subprocess.run([sys.executable, os.path.join(ROOT, "rsvp.py"), "dry-run", "--out", out],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            mdir = os.path.join(out, "sample-tidewater-m1")
            with open(os.path.join(mdir, "report.md")) as fh:
                fresh = fh.read()
            with open(os.path.join(ROOT, "sample", "sample_report.md")) as fh:
                committed = fh.read()
            self.assertEqual(fresh, committed)
            self.assertIn("**Illustrative.**", fresh)
            with open(os.path.join(mdir, "runlog.jsonl")) as fh:
                fresh_log = fh.read()
            self.assertEqual(len(fresh_log.splitlines()), 300)
            with open(os.path.join(ROOT, "sample", "sample_runlog.jsonl")) as fh:
                self.assertEqual(fresh_log, fh.read())
            with open(os.path.join(mdir, "coded_runlog.csv")) as fh:
                fresh_coded = fh.read()
            with open(os.path.join(ROOT, "sample", "sample_coded_runlog.csv")) as fh:
                self.assertEqual(fresh_coded, fh.read())
        finally:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
