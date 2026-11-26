# Changelog

Versions of the kit follow MAJOR.MINOR.PATCH. A change to a counting or reporting rule raises the minor number and is listed here with its date. The method version the kit implements is recorded in every measurement manifest.

## 0.1.1: 2026-11-27

Docs, a roadmap and checks. No counting or reporting rule changed.

### Added

- The [Roadmap](https://github.com/tanmaypatange/rsvp/wiki/Roadmap): RSVP is at v0.1, in Phase 0: Foundation, and the planned phases after it have no dates.
- A status line on the README and the wiki home page: work in progress, RSVP v0.1, Phase 0 (Foundation).

- The RSVP docs, published as 27 pages in the [wiki](https://github.com/tanmaypatange/rsvp/wiki): the guide, the seven measures, the reporting rules, the sample report, the limitations, the roadmap and the credits and references, with a page on installing and running the kit. The repository holds only the kit.
- `validate` prints a notice, not an error, for engines outside three to six and for unbranded prompts per intent outside four to eight. Tests cover it.
- The README opens with the docs home page (about RSVP, the seven measures, start here, a list of every wiki page), then the kit sections, and states the pilot and directional defaults.

### Changed

- The report labels the kit's own number **Kit release**, next to the **Method** it implements (RSVP v0.1).

### Removed

- `bands.visibility_bounds` and its test. The report states the exact visibility rate from the run log, so the helper was never called.

## 0.1.0: 2026-11-26

First version of the kit, implementing RSVP v0.1.

### Added

- `sample/sample_runlog.jsonl`, `sample/sample_coded_runlog.csv` and `sample/README.md`: the raw log and coded log the sample report is built from, with an explanation of each stage. The tests check that a fresh dry run reproduces all three sample files byte for byte.
- `config.example.yaml` and `prompts.template`: the pre-registered protocol, validated before any run.
- Runner with separate engine adapters (`openai_responses`, `perplexity`, `fake`): fresh context per run, no follow-ups, at most three attempts for technical failures only, runs spread across days and shuffled within each day, declared location passed by setting or prompt sentence as recorded.
- Counter: mention flag per run with aliases and exclusions, citation by registrable domain with tracking parameters stripped and redirects resolved, ghost citations, three exclusive position bands.
- Reporter: visibility, mention and citation rates with 95% Wilson bands per engine and declared location, mention rate by intent, share of voice as counts with its denominator, cell classes, Jaccard overlap, day-by-day rates, a fixed slot per reporting rule, refusal of a report with an empty slot, pilot label and directional wording.
- Run log: append-only rows, config hash at the start of a measurement, a new measurement ID when the protocol changes, change list and deviations.
- Second-analyst recode sample and agreement.
- Dry run on bundled fictional data, and the illustrative sample report it produces.
- Tests for every rule above, including the Wilson band checks and an end-to-end dry run.
