import copy
import os
import unittest

import tests  # noqa: F401
from tests.helpers import BASE, Workspace
import config as config_mod
import yamlsubset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def problems(**changes):
    cfg = copy.deepcopy(BASE)
    cfg.update({k: v for k, v in config_mod.DEFAULTS.items() if k not in cfg})
    cfg["_base_dir"] = "."
    for k, v in changes.items():
        cfg[k] = v
    try:
        config_mod.validate(cfg)
    except config_mod.ConfigError as exc:
        return exc.problems
    return []


class Validation(unittest.TestCase):
    def test_base_is_valid(self):
        self.assertEqual(problems(), [])

    def test_two_to_four_competitors(self):
        one = [{"name": "Birch Ledger"}]
        five = [{"name": "C%d" % i} for i in range(5)]
        self.assertTrue(any("two to four" in p for p in problems(competitors=one)))
        self.assertTrue(any("two to four" in p for p in problems(competitors=five)))

    def test_one_intent_label_per_prompt(self):
        prompts = copy.deepcopy(BASE["prompts"])
        prompts[0]["intent"] = "navigational"
        self.assertTrue(any("intent label" in p for p in problems(prompts=prompts)))
        prompts[0]["intent"] = None
        self.assertTrue(any("intent label" in p for p in problems(prompts=prompts)))

    def test_need_id_required(self):
        prompts = copy.deepcopy(BASE["prompts"])
        del prompts[0]["need"]
        self.assertTrue(any("need ID" in p for p in problems(prompts=prompts)))

    def test_unbranded_prompt_may_not_name_the_brand(self):
        prompts = copy.deepcopy(BASE["prompts"])
        prompts[0]["text"] = "Is Acme good for a bakery?"
        self.assertTrue(any("names the client brand" in p for p in problems(prompts=prompts)))
        prompts[0]["branded"] = True
        self.assertEqual(problems(prompts=prompts), [])

    def test_branded_prompt_must_name_the_brand(self):
        prompts = copy.deepcopy(BASE["prompts"])
        prompts[0]["branded"] = True
        self.assertTrue(any("marked branded" in p for p in problems(prompts=prompts)))

    def test_every_engine_needs_a_location_method(self):
        engines = copy.deepcopy(BASE["engines"])
        engines[0]["location_method"] = None
        self.assertTrue(any("location_method" in p for p in problems(engines=engines)))

    def test_runs_must_be_positive(self):
        self.assertTrue(any("runs_per_prompt" in p for p in problems(runs_per_prompt=0)))

    def test_real_adapter_needs_a_model(self):
        engines = [{"id": "x", "adapter": "openai_responses", "mode": "search-on", "interface": "api",
                    "location_method": "setting"}]
        self.assertTrue(any("model is required" in p for p in problems(engines=engines)))


class Notices(unittest.TestCase):
    def test_no_notice_inside_the_working_ranges(self):
        cfg = copy.deepcopy(BASE)
        cfg["engines"] = [{"id": "e%d" % i} for i in range(3)]
        cfg["prompts"] = [{"id": "p%d" % (3 * i + j), "intent": intent, "need": "n"}
                          for j, intent in enumerate(("informational", "commercial", "transactional"))
                          for i in range(4)]
        self.assertEqual(config_mod.notices(cfg), [])

    def test_notice_for_engines_and_prompts_outside_the_ranges(self):
        cfg = copy.deepcopy(BASE)
        cfg["engines"] = [{"id": "e1"}]
        cfg["prompts"] = [{"id": "p1", "intent": "informational", "need": "n"}]
        found = config_mod.notices(cfg)
        self.assertTrue(any("engines" in n and "three to six" in n for n in found))
        self.assertTrue(any("informational" in n and "four to eight" in n for n in found))
        self.assertTrue(any("commercial" in n for n in found))

    def test_branded_prompts_are_not_counted(self):
        cfg = copy.deepcopy(BASE)
        cfg["engines"] = [{"id": "e%d" % i} for i in range(3)]
        cfg["prompts"] = [{"id": "p%d" % i, "intent": "commercial", "need": "n", "branded": True}
                          for i in range(5)]
        self.assertTrue(any("0 unbranded commercial" in n for n in config_mod.notices(cfg)))


class Files(unittest.TestCase):
    def test_example_config_parses_and_asks_to_be_filled(self):
        raw = yamlsubset.load(os.path.join(ROOT, "config.example.yaml"))
        self.assertEqual(raw["runs_per_prompt"], 10)
        self.assertEqual(raw["brand"]["name"], "")
        with self.assertRaises(config_mod.ConfigError) as ctx:
            ws = Workspace()
            try:
                import shutil
                shutil.copy(os.path.join(ROOT, "config.example.yaml"), os.path.join(ws.dir, "config.yaml"))
                shutil.copy(os.path.join(ROOT, "prompts.template"), os.path.join(ws.dir, "prompts.yaml"))
                config_mod.load(os.path.join(ws.dir, "config.yaml"))
            finally:
                ws.close()
        text = "\n".join(ctx.exception.problems)
        self.assertIn("brand.name is required", text)
        self.assertIn("intent label", text)

    def test_prompts_template_is_blank_with_one_intent_slot_each(self):
        raw = yamlsubset.load(os.path.join(ROOT, "prompts.template"))
        for p in raw["prompts"]:
            self.assertIn("intent", p)
            self.assertIsNone(p["intent"])
            self.assertEqual(p["text"], "")
            self.assertTrue(p["need"])

    def test_sample_config_is_valid(self):
        cfg = config_mod.load(os.path.join(ROOT, "sample", "config.sample.yaml"))
        self.assertEqual(len(cfg["competitors"]), 3)


class Hash(unittest.TestCase):
    def test_operational_keys_do_not_change_the_hash(self):
        a = copy.deepcopy(BASE)
        b = copy.deepcopy(BASE)
        b["timeout_seconds"] = 999
        self.assertEqual(config_mod.protocol_hash(a), config_mod.protocol_hash(b))

    def test_alias_change_changes_the_hash(self):
        a = copy.deepcopy(BASE)
        b = copy.deepcopy(BASE)
        b["brand"]["aliases"].append("Acme App")
        self.assertNotEqual(config_mod.protocol_hash(a), config_mod.protocol_hash(b))
        changed, detail = config_mod.changed_sections(config_mod.protocol(a), config_mod.protocol(b))
        self.assertEqual(changed, ["brand"])
        self.assertEqual(detail, ["brand.aliases"])


class YamlSubset(unittest.TestCase):
    def test_block_and_flow(self):
        text = """
# comment
a: 1
b: "two # not a comment"
c: [x, 'y z', 3]
d:
  e: true
  f: ~
g:
  - {id: P1, text: "Hi, there", tags: [a, b]}
  - id: P2
    text: plain text: with colon
h:
- 1
- 2.5
"""
        data = yamlsubset.loads(text)
        self.assertEqual(data["a"], 1)
        self.assertEqual(data["b"], "two # not a comment")
        self.assertEqual(data["c"], ["x", "y z", 3])
        self.assertEqual(data["d"], {"e": True, "f": None})
        self.assertEqual(data["g"][0], {"id": "P1", "text": "Hi, there", "tags": ["a", "b"]})
        self.assertEqual(data["g"][1], {"id": "P2", "text": "plain text: with colon"})
        self.assertEqual(data["h"], [1, 2.5])

    def test_errors_carry_line_numbers(self):
        with self.assertRaises(yamlsubset.YamlError) as ctx:
            yamlsubset.loads("a: 1\na: 2\n")
        self.assertIn("line 2", str(ctx.exception))
        with self.assertRaises(yamlsubset.YamlError):
            yamlsubset.loads("a: &anchor 1\n")


if __name__ == "__main__":
    unittest.main()
