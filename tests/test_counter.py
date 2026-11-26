import copy
import unittest

import tests  # noqa: F401
from tests.helpers import BASE
import counter


def record(text, sources=(), status="ok", prompt="P1", prompt_text="Best bookkeeping app for a bakery", **kw):
    r = {"run": "R00001", "engine": "e1", "location": "United States", "prompt": prompt,
         "prompt_text": prompt_text, "status": status, "answer_text": text,
         "sources": [s if isinstance(s, dict) else {"url": s} for s in sources],
         "sent_at": "2026-11-02T09:00:00+00:00"}
    r.update(kw)
    return r


def code(text, sources=(), status="ok", **kw):
    return counter.code_record(record(text, sources, status, **kw), copy.deepcopy(BASE))


class MentionRules(unittest.TestCase):
    def test_full_or_short_name_counts(self):
        self.assertTrue(code("Try Acme Books for invoices.")["mention"])
        self.assertTrue(code("Try Acme for invoices.")["mention"])

    def test_alias_on_the_list_counts(self):
        self.assertTrue(code("AcmeBooks is simple.")["mention"])

    def test_whole_words_only(self):
        self.assertFalse(code("Acmeville has a market.")["mention"])

    def test_case_and_quotes_are_folded(self):
        self.assertTrue(code("\u201cACME BOOKS\u201d is fine.")["mention"])

    def test_counted_once_per_run(self):
        row = code("Acme Books, Acme Books and Acme again.")
        self.assertIs(row["mention"], True)
        self.assertEqual(row["brands"].count("Acme Books"), 1)

    def test_exclusion_list_blocks_a_lookalike(self):
        row = code("Acme Capital lends to small firms.")
        self.assertFalse(row["mention"])
        self.assertTrue(code("Acme Capital lends money; Acme Books does accounts.")["mention"])

    def test_domain_cited_without_name_is_a_citation_not_a_mention(self):
        row = code("Birch Ledger is popular.", ["https://acmebooks.example/guide"])
        self.assertFalse(row["mention"])
        self.assertTrue(row["cited"])
        self.assertTrue(row["ghost"])

    def test_pronoun_or_the_company_does_not_count(self):
        self.assertFalse(code("The company behind it is small, and it is well liked.")["mention"])

    def test_name_only_inside_the_restated_question_does_not_count(self):
        row = code("You asked: Is Acme Books good for a bakery? Most bakeries pick Birch Ledger.",
                   prompt_text="Is Acme Books good for a bakery?")
        self.assertFalse(row["mention"])

    def test_bad_example_still_counts(self):
        self.assertTrue(code("Avoid Acme Books if you need payroll.")["mention"])

    def test_competitors_counted_by_the_same_rule(self):
        row = code("Birch Ledger and Cedar Accounts, and Birch Ledger again.")
        self.assertEqual(row["comp"], ["Birch Ledger", "Cedar Accounts"])


class CitationRules(unittest.TestCase):
    def test_subdomain_counts(self):
        self.assertTrue(code("x", ["https://help.acmebooks.example/a/1"])["cited"])

    def test_tracking_parameters_are_stripped(self):
        self.assertEqual(counter.strip_tracking("https://A.example/p?utm_source=x&id=3&gclid=9&ref=y"),
                         "https://a.example/p?id=3")

    def test_redirect_is_resolved_before_matching(self):
        src = {"url": "https://go.short.example/r/abc",
               "resolved_url": "https://www.acmebooks.example/pricing?utm_medium=a"}
        self.assertTrue(code("x", [src])["cited"])
        self.assertFalse(code("x", ["https://go.short.example/r/abc"])["cited"])

    def test_two_pages_of_one_domain_are_one_citation(self):
        row = code("x", ["https://acmebooks.example/a", "https://www.acmebooks.example/b"])
        self.assertEqual(row["domains"], ["acmebooks.example"])

    def test_copy_on_another_domain_does_not_count(self):
        self.assertFalse(code("x", ["https://mirror.example/acmebooks.example/guide"])["cited"])

    def test_registrable_domain(self):
        rd = counter.registrable_domain
        self.assertEqual(rd("www.shop.brand.co.uk"), "brand.co.uk")
        self.assertEqual(rd("a.b.brand.com"), "brand.com")
        self.assertEqual(rd("brand.com"), "brand.com")
        self.assertEqual(rd("x.brand.com.de", ["com.de"]), "brand.com.de")

    def test_run_with_no_citations_stays_valid(self):
        row = code("Acme Books is fine.")
        self.assertTrue(row["valid"])
        self.assertFalse(row["cited"])
        self.assertEqual(row["domains"], [])

    def test_four_cases(self):
        both = code("Acme Books", ["https://acmebooks.example"])
        m_only = code("Acme Books", ["https://other.example"])
        ghost = code("Birch Ledger", ["https://acmebooks.example"])
        neither = code("Birch Ledger", ["https://other.example"])
        self.assertEqual([(r["mention"], r["cited"], r["ghost"]) for r in (both, m_only, ghost, neither)],
                         [(True, True, False), (True, False, False), (False, True, True), (False, False, False)])


class PositionRules(unittest.TestCase):
    def test_bands_are_exclusive(self):
        self.assertEqual(counter.position_band(1), "first")
        self.assertEqual(counter.position_band(2), "second_third")
        self.assertEqual(counter.position_band(3), "second_third")
        self.assertEqual(counter.position_band(4), "fourth_later")
        self.assertIsNone(counter.position_band(0))

    def test_numbered_list_order_with_bold_lead_in(self):
        row = code("Here are options:\n1. **Birch Ledger** is big.\n2. **Acme Books** is simple.")
        self.assertEqual(row["pos"], 2)
        self.assertEqual(row["pos_band"], "second_third")

    def test_table_rows_top_to_bottom_left_to_right(self):
        row = code("| Tool | Note |\n|---|---|\n| Birch Ledger | Dune Pay is cheaper |\n| Cedar Accounts | x |\n| Acme Books | y |")
        self.assertEqual(row["brands"], ["Birch Ledger", "Dune Pay", "Cedar Accounts", "Acme Books"])
        self.assertEqual(row["pos_band"], "fourth_later")

    def test_brand_named_twice_uses_first_appearance(self):
        row = code("Acme Books first, then Birch Ledger, then Acme Books again.")
        self.assertEqual(row["pos"], 1)

    def test_closing_line_gives_the_position(self):
        row = code("Birch Ledger and Cedar Accounts lead. Elm Tax is cheap.\nOther options include Acme Books.")
        self.assertEqual(row["pos"], 4)

    def test_all_brands_named_count_for_order(self):
        row = code("Dune Pay, Elm Tax and Acme Books.")
        self.assertEqual(row["pos"], 3)
        self.assertEqual(row["comp"], [])

    def test_no_position_without_mention(self):
        row = code("Birch Ledger only.")
        self.assertEqual((row["pos"], row["pos_band"]), (0, None))

    def test_sponsored_blocks_stay_out_of_the_order(self):
        rec = record("Birch Ledger is good.", sponsored=["Acme Books: sponsored offer"])
        row = counter.code_record(rec, copy.deepcopy(BASE))
        self.assertFalse(row["mention"])


class Validity(unittest.TestCase):
    def test_failed_runs_are_not_valid(self):
        for status in ("error", "empty", "timeout"):
            row = code("Acme Books", ["https://acmebooks.example"], status=status)
            self.assertFalse(row["valid"])
            self.assertFalse(row["mention"])

    def test_refusal_is_valid_with_no_mention(self):
        row = code("I cannot recommend products.", status="refused")
        self.assertTrue(row["valid"])
        self.assertFalse(row["mention"])


class ChangeList(unittest.TestCase):
    def test_correction_is_applied_and_ghost_recomputed(self):
        rows = [code("Birch Ledger", ["https://acmebooks.example"])]
        rows[0]["run"] = "R00001"
        applied = counter.apply_changes(rows, [{"run": "R00001", "field": "pos", "new": 2},
                                               {"run": "R00001", "field": "mention", "new": 1}])
        self.assertEqual(len(applied), 2)
        self.assertTrue(rows[0]["mention"])
        self.assertFalse(rows[0]["ghost"])
        self.assertEqual(rows[0]["pos_band"], "second_third")


if __name__ == "__main__":
    unittest.main()
