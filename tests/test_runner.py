import json
import os
import unittest
from collections import Counter, defaultdict

import tests  # noqa: F401
from tests.helpers import BASE, Workspace, canned_all, ok
import engines
import runlog
import runner
from engines.fake import FakeAdapter


class Recording(FakeAdapter):
    calls = []

    def call(self, request):
        Recording.calls.append(request)
        return super().call(request)


class Plan(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def test_every_location_engine_prompt_run(self):
        cfg = self.ws.config(canned_all([ok("x")], engines=("e1", "e2")),
                             engines=[dict(BASE["engines"][0]), dict(BASE["engines"][0], id="e2")],
                             locations=[{"label": "United States", "country": "US"},
                                        {"label": "Boise, Idaho, United States", "country": "US", "city": "Boise"}])
        plan = runner.expand(cfg)
        self.assertEqual(len(plan), 2 * 2 * 2 * 4)
        keys = {(p["location"], p["engine"], p["prompt"], p["run_number"]) for p in plan}
        self.assertEqual(len(keys), len(plan))

    def test_each_cell_spread_across_days_and_shuffled_within_day(self):
        cfg = self.ws.config(canned_all([ok("x")]), runs_per_prompt=10, schedule_days=5)
        plan = runner.schedule(runner.expand(cfg), seed=3)
        per_cell_day = defaultdict(Counter)
        for p in plan:
            per_cell_day[(p["engine"], p["prompt"])][p["day"]] += 1
        for cnt in per_cell_day.values():
            self.assertEqual(sorted(cnt.items()), [(d, 2) for d in range(1, 6)])
        day1 = [p["prompt"] for p in plan if p["day"] == 1]
        self.assertNotEqual(day1, sorted(day1))


class Running(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        engines.ADAPTERS["recording"] = "tests.test_runner:Recording"
        Recording.calls = []

    def tearDown(self):
        engines.ADAPTERS.pop("recording", None)
        self.ws.close()

    def test_fresh_context_one_call_per_run_no_follow_up(self):
        eng = dict(BASE["engines"][0], adapter="recording")
        cfg, m = self.ws.run(canned_all([ok("Acme Books")]), engines=[eng])
        self.assertEqual(len(Recording.calls), len(m.plan()))
        texts = {c.prompt_text for c in Recording.calls}
        self.assertEqual(texts, {p["text"] for p in BASE["prompts"]})
        self.assertFalse(any(hasattr(c, "messages") or hasattr(c, "history") for c in Recording.calls))

    def test_stores_answer_sources_time_and_error(self):
        canned = canned_all([ok("Acme Books", ["https://acmebooks.example/a"]),
                             {"fail_attempts": 3, "fail_status": "error", "error": "HTTP 500"}])
        cfg, m = self.ws.run(canned)
        recs = m.records()
        self.assertEqual(len(recs), len(m.plan()))
        good = [r for r in recs if r["status"] == "ok"][0]
        self.assertEqual(good["answer_text"], "Acme Books")
        self.assertEqual(good["location_method"], "setting")
        self.assertEqual(good["network_location"], "test network")
        self.assertEqual(good["sources"][0]["url"], "https://acmebooks.example/a")
        self.assertTrue(good["sent_at"] and good["received_at"])
        bad = [r for r in recs if r["status"] == "error"][0]
        self.assertEqual(bad["error_detail"], "HTTP 500")
        self.assertEqual(bad["attempt"], 3)
        self.assertEqual(len(bad["attempt_errors"]), 3)

    def test_retry_recovers_after_a_technical_failure(self):
        cfg, m = self.ws.run(canned_all([ok("Acme Books", fail_attempts=2, fail_status="timeout")]))
        recs = m.records()
        self.assertTrue(all(r["status"] == "ok" and r["attempt"] == 3 for r in recs))

    def test_content_is_never_retried(self):
        eng = dict(BASE["engines"][0], adapter="recording")
        cfg, m = self.ws.run(canned_all([{"status": "refused", "text": "I cannot help."}]), engines=[eng])
        self.assertEqual(len(Recording.calls), len(m.plan()))

    def test_empty_body_is_a_failure(self):
        cfg, m = self.ws.run(canned_all([ok("   ")]))
        self.assertTrue(all(r["status"] == "empty" for r in m.records()))

    def test_location_sentence_for_prompt_method(self):
        eng = dict(BASE["engines"][0], adapter="recording", location_method="prompt")
        self.ws.run(canned_all([ok("x")]), engines=[eng])
        self.assertTrue(all(c.prompt_text.startswith("I am in United States. ") for c in Recording.calls))

    def test_location_setting_lost_stops_engine_without_switching(self):
        eng = dict(BASE["engines"][0], adapter="recording",
                   options={"canned_file": "canned.json", "drop_location_setting": True})
        cfg, m = self.ws.run(canned_all([ok("x")]), engines=[eng])
        self.assertEqual(m.records(), [])
        dev = m.deviations()
        self.assertEqual(dev[0]["kind"], "engine_stopped")
        self.assertTrue(all(c.location_method == "setting" for c in Recording.calls))

    def test_redirects_resolved_and_raw_url_kept(self):
        resolver = runner.RedirectResolver(enabled=False, static_map={
            "https://go.example/r/1": "https://acmebooks.example/p"})
        cfg, m = self.ws.run(canned_all([ok("x", ["https://go.example/r/1"])]), resolver=resolver)
        src = m.records()[0]["sources"][0]
        self.assertEqual(src["url"], "https://go.example/r/1")
        self.assertEqual(src["resolved_url"], "https://acmebooks.example/p")

    def test_resume_skips_runs_already_logged(self):
        cfg, m = self.ws.run(canned_all([ok("x")]))
        n = len(m.records())
        m2 = runner.run_measurement(cfg, clock=runner.SimulatedClock("2026-11-02"), all_days=True,
                                    resolver=runner.RedirectResolver(enabled=False), log=lambda *a: None)
        self.assertEqual(m2.id, m.id)
        self.assertEqual(len(m2.records()), n)

    def test_one_day_per_invocation_and_no_second_day_on_the_same_date(self):
        cfg = self.ws.config(canned_all([ok("x")]))
        clock = runner.SimulatedClock("2026-11-02")
        quiet = dict(resolver=runner.RedirectResolver(enabled=False), log=lambda *a: None)
        m = runner.run_measurement(cfg, clock=clock, **quiet)
        self.assertEqual({r["day"] for r in m.records()}, {1})
        m = runner.run_measurement(cfg, clock=clock, **quiet)
        self.assertEqual({r["day"] for r in m.records()}, {1})
        clock.start_day(2)
        m = runner.run_measurement(cfg, clock=clock, **quiet)
        self.assertEqual({r["day"] for r in m.records()}, {1, 2})

    def test_keys_are_never_stored(self):
        with open(os.path.join(self.ws.dir, "keys.env"), "w") as fh:
            fh.write("SECRET_KEY=sk-should-not-appear\n")
        cfg, m = self.ws.run(canned_all([ok("x")]))
        with open(m.path("runlog.jsonl")) as fh:
            self.assertNotIn("sk-should-not-appear", fh.read())


class RunLog(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()

    def tearDown(self):
        self.ws.close()

    def test_config_is_hashed_when_a_measurement_starts(self):
        cfg, m = self.ws.run(canned_all([ok("x")]))
        man = m.manifest
        import config as config_mod
        self.assertEqual(man["config_hash"], config_mod.protocol_hash(cfg))
        self.assertTrue(all(r["config_hash"] == man["config_hash"] for r in m.records()))
        with open(m.path("protocol.json")) as fh:
            self.assertEqual(json.load(fh)["brand"]["aliases"], ["Acme", "AcmeBooks"])

    def test_changed_aliases_start_a_new_measurement_id(self):
        cfg, m1 = self.ws.run(canned_all([ok("x")]))
        brand = dict(BASE["brand"], aliases=["Acme", "AcmeBooks", "Acme App"])
        cfg2, m2 = self.ws.run(canned_all([ok("x")]), brand=brand)
        self.assertNotEqual(m1.id, m2.id)
        self.assertEqual(m2.id, "t-m2")
        self.assertIn("brand.aliases", m2.manifest["changed_detail"])
        index = runlog.read_jsonl(os.path.join(cfg["output_dir"], "index.jsonl"))
        self.assertEqual([e["measurement_id"] for e in index], ["t-m1", "t-m2"])
        self.assertEqual(len(m1.records()), len(m1.plan()))
        self.assertTrue(all(r["measurement_id"] == "t-m2" for r in m2.records()))

    def test_log_is_append_only(self):
        cfg, m = self.ws.run(canned_all([ok("x")]))
        with self.assertRaises(ValueError):
            m.append_record({"measurement_id": "other", "run": "R1"})
        with open(m.path("runlog.jsonl")) as fh:
            lines = fh.read().splitlines()
        self.assertEqual(len(lines), len(m.plan()))


if __name__ == "__main__":
    unittest.main()
