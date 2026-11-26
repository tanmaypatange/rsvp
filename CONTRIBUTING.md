# Contributing

Thank you for helping. Small, focused changes are easiest to review. The method docs are in the [wiki](https://github.com/tanmaypatange/rsvp/wiki), and planned work is in the [Roadmap](https://github.com/tanmaypatange/rsvp/wiki/Roadmap).

## Kinds of contribution

- **Add an engine adapter.** Add one small file in `engines/` with one class that subclasses `engines.Adapter`, and register it in `engines.ADAPTERS`. The adapter sends one prompt in a fresh context, with no earlier messages, and returns an `EngineResponse`. It does not retry, edit answers or store anything; the runner does that. Put cited sources in `sources` exactly as the engine returns them. Return `refused` only when the engine signals a refusal. If the engine's location setting stops working, raise `LocationSettingUnavailable`, so the runner can stop the engine and log a deviation instead of switching silently.
- **Fix a rule.** Every counting and reporting rule has one code path and at least one test (see the table below). Change both together. If a change alters a definition or a rule, say so in `CHANGELOG.md`.
- **Add a test.** Tests use the fake adapter and a temporary folder (`tests/helpers.py`). They never call a real engine.
- **Add a source.** Cite only papers listed in the [credits and references](https://github.com/tanmaypatange/rsvp/wiki/Credits-and-references), by author and year, with a link. Say what the paper found and add no opinion about it.

## Steps

1. Fork the repository.
2. Create a branch for one change.
3. Make the change, with its test. Run the suite and the dry run:

   ```bash
   python3 -m unittest discover -s tests -t .
   ```

   ```bash
   python3 rsvp.py dry-run
   ```

   If your change alters the sample report on purpose, regenerate it with `python3 rsvp.py dry-run --write-sample` and explain the difference.
4. Open a pull request that says what changed and why.

## Ground rules

- Standard library only, plus at most one HTTP client. No other dependencies.
- No API keys in the repository. `keys.env` is gitignored.
- Do not loosen or skip a test to make it pass.
- Every number in code traces to the RSVP method. Example numbers are labelled illustrative.
- No em dashes in code, docs, templates or commit messages.
- Commit messages are conventional (`feat`, `fix`, `docs`, `chore`) with a short reason in the body.

## Where each rule lives

| Rule | Code | Test |
|---|---|---|
| Close the alias list before the first run; changed aliases start a new measurement ID | `runlog.start_or_resume`, `config.protocol_hash` | `test_runner.RunLog` |
| A run counts once however often the name appears | `counter.code_record` | `test_counter.MentionRules.test_counted_once_per_run` |
| Mention edge cases: alias, exclusion, pronoun, restated question, bad example | `counter.find_brands` | `test_counter.MentionRules` |
| A domain link without the name is a citation (ghost) | `counter.code_record` | `test_counter.CitationRules.test_four_cases` |
| Citation: registrable domain, subdomains, tracking stripped, redirects resolved | `counter.clean_source`, `runner.RedirectResolver` | `test_counter.CitationRules`, `test_runner.Running.test_redirects_resolved_and_raw_url_kept` |
| Three exclusive position bands, only for runs with a mention | `counter.position_band` | `test_counter.PositionRules`, `test_reporter.Figures.test_position_bands_add_up_to_mentions` |
| Visibility rate: mention or citation over valid runs | `reporter.headline_figures` | `test_reporter.Figures.test_headline_has_counts_and_bands` |
| 95% Wilson band | `bands.wilson` | `test_bands.WilsonBand` |
| Fresh context for every run, no follow-up | `runner.run_measurement`, `engines/` | `test_runner.Running.test_fresh_context_one_call_per_run_no_follow_up` |
| Failed runs logged and left out of the denominator; no-citation runs stay in | `counter.code_record`, `runner` | `test_counter.Validity`, `test_reporter.Figures.test_failed_runs_left_out_of_the_denominator` |
| Retry only technical failures, at most three attempts | `runner.run_measurement` | `test_runner.Running` |
| Share of voice: fixed set, counts and denominator, no band | `reporter.slot_share_of_voice` | `test_reporter.Figures.test_share_of_voice_counts_with_denominator_and_no_band` |
| Cell classes never, rarely, flipping, mostly, always | `bands.cell_class` | `test_bands.OtherStatistics.test_cell_classes` |
| Jaccard overlap of brands and domains per cell | `bands.mean_pairwise_jaccard` | `test_bands.OtherStatistics.test_jaccard` |
| Reporting rule 1: range and sample size | `reporter.slot_rule1` | `test_reporter.Figures.test_headline_has_counts_and_bands` |
| Reporting rule 2: split by engine and declared location | `reporter.slot_rule2_split`, `reporter.Data.pairs` | `test_reporter.Figures.test_split_by_engine_and_location_no_pooled_row` |
| Reporting rule 3: prompt list and share of voice details | `reporter.slot_prompt_list`, `reporter.slot_share_of_voice` | `test_reporter.Figures.test_prompt_list_with_intent_labels_attached` |
| Reporting rule 4: dates of this and the next measurement | `reporter.slot_rule4_dates`, `reporter.slot_rule4_next` | `test_reporter.Figures.test_dates_and_next_measurement` |
| Reporting rule 5: pilot label | `reporter.slot_rule5` | `test_reporter.Figures.test_pilot_label_and_directional_wording` |
| Reporting rule 6: directional wording | `reporter.slot_rule6` | `test_reporter.Figures.test_directional_when_bands_are_wide_even_if_not_a_pilot` |
| Refuse a report with an empty slot, and the other refusal conditions | `reporter.render`, `reporter.refusals` | `test_reporter.Refusals` |
| Spread runs across days, shuffle within a day | `runner.expand`, `runner.schedule` | `test_runner.Plan` |
| Location passed as recorded; never switched silently | `runner.prompt_text_for`, `engines.LocationSettingUnavailable` | `test_runner.Running` |
| Validate the protocol before any run | `config.validate` | `test_config.Validation` |
| Second-analyst recode and agreement | `counter.write_recode_sample`, `counter.agreement` | `test_reporter.QualityChecks` |
| Corrections in a change list, originals kept | `counter.apply_changes` | `test_counter.ChangeList`, `test_reporter.Figures.test_change_list_is_applied_and_counted` |
