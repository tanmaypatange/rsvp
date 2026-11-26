# rsvp

A runnable kit for RSVP (Repeated Sampling of Visibility and Position). It repeats each buyer question many times on each AI engine, then reports how often and where a brand shows up, as a rate with a 95% Wilson band.

One config file, one command, one report.

## What is in the kit

1. **`config.example.yaml`**: the brand, domain, aliases, exclusions, two to four competitors, the prompt list, the engines, the declared location, runs per prompt and the pilot threshold.
2. **`prompts.template`**: a blank prompt list, one intent label and one need ID per prompt.
3. **Runner** (`runner.py`, adapters in `engines/`): sends every location x engine x prompt x run in a fresh context, with no follow-ups, and stores the answer, sources, time and any error.
4. **Counter** (`counter.py`): codes each run for mention, citation, ghost citation and position.
5. **Reporter** (`reporter.py`, `report_template.md`): computes the rates, bands, share of voice and run spread, and writes the one-page report. It refuses to write a report with an empty slot.
6. **Run log** (`runlog.py`): one row per run, append only. The config is hashed when a measurement starts.
7. **Sample report** (`sample/sample_report.md`): built by the dry run from made-up canned answers, labelled illustrative.

Plus `rsvp.py` (the command line), `bands.py` (the Wilson band and other statistics), `config.py`, `yamlsubset.py` (a small YAML reader), and `tests/`.

## Install

You need Python 3.8 or later (tested on 3.13). There is nothing else to install: the kit uses only the standard library, including its HTTP client.

```bash
git clone <your fork> rsvp && cd rsvp
```

## Try it first: the dry run

```bash
python3 rsvp.py dry-run
```

This runs the real runner, counter, reporter and run log on bundled fictional data, with a fake engine that returns canned answers. No engine is called and no key is needed. It writes `measurements-dry-run/sample-tidewater-m1/report.md`, which matches `sample/sample_report.md`.

## Run a measurement

1. Copy the config and the prompt list, then fill both in.

   ```bash
   cp config.example.yaml config.yaml
   ```

   ```bash
   cp prompts.template prompts.yaml
   ```

2. Put your engine keys in `keys.env`, one `NAME=value` per line, with the names used in `key_env`. The file is gitignored. Keys are never written to the run log or the report.

3. Check the config.

   ```bash
   python3 rsvp.py validate --config config.yaml
   ```

4. Run. Each call runs the next scheduled day. Run the same command once a day until the plan is done; the report is written after the last run.

   ```bash
   python3 rsvp.py run --config config.yaml
   ```

## Config

The config is the pre-registered protocol. Every key is commented in `config.example.yaml`. Key points:

- **Brand and aliases.** Close the alias list before the first run. Changing the aliases, or anything else in the protocol, starts a new measurement ID; runs of two measurement IDs are never mixed.
- **Competitors.** Two to four, fixed before the first run. Other brands are logged and listed, never counted in share of voice.
- **Prompts.** One label per prompt: `informational`, `commercial` or `transactional`. Paraphrases of one need share a need ID. The headline list is unbranded. Prompts that name the client go in a labelled branded block (`branded: true`).
- **Engines.** Adapters: `openai_responses`, `perplexity` and `fake`; see CONTRIBUTING.md to add one. Treat two modes of one product as two engines. `location_method` is `setting` (the engine's location setting) or `prompt` (a sentence at the start of the prompt).
- **Runs.** `runs_per_prompt` is the sample size, spread across `schedule_days`. There is no minimum: choose it from the band width your decision needs. Start with a pilot.
- **Reporting.** `pilot_threshold`, `first_measurement`, `directional_band_width` and `remeasure_weeks` set the pilot label, the directional wording and the next measurement date.

## Outputs

Each measurement gets a folder under `measurements/<measurement_id>/`:

| File | What it holds |
|---|---|
| `manifest.json` | Measurement ID, config hash, code and method version, planned runs |
| `protocol.json` | The protocol as hashed at the start |
| `plan.json` | Every planned run with its day and order |
| `runlog.jsonl` | One row per run, append only: prompt sent, answer, sources (raw and resolved), status, error, times |
| `changes.jsonl` | Corrections to the coding; the original rows are kept |
| `deviations.jsonl` | Deviations found while running, for example an engine stopped |
| `coded_runlog.csv` | The counter's coding of every run, rebuilt with each report |
| `report.md` | The one-page report and its method note |

`measurements/index.jsonl` lists every measurement ID with its config hash.

## Quality checks

A second analyst recodes a random 10% of valid runs blind, and the report shows the agreement:

```bash
python3 rsvp.py recode-sample --measurement measurements/<id>
```

```bash
python3 rsvp.py agreement --measurement measurements/<id> --file measurements/<id>/recode_sample.csv
```

Use `--n 10` on `recode-sample` for the dry-run check of about ten answers before the first real run. To correct a coding error, add a row to the change list and rebuild the report:

```bash
python3 rsvp.py correct --measurement measurements/<id> --run R00042 --field mention --new 1 --reason "alias split by a line break"
```

```bash
python3 rsvp.py report --measurement measurements/<id>
```

## Test

```bash
python3 -m unittest discover -s tests -t .
```

The tests cover every counting and reporting rule the kit implements, the refusal conditions, and an end-to-end dry run that must reproduce `sample/sample_report.md` exactly. The Wilson test reproduces 4 of 10 as 17 to 69, 12 of 30 as 25 to 58, 0 of 30 as 0 to 11, 30 of 30 as 89 to 100 and 103 of 349 as 25 to 35.

## RSVP decisions the kit applies

These choices are RSVP decisions, not published findings:

- 95% Wilson bands for every rate; none for share of voice in v0.1, because mentions within one run are not independent trials.
- Three exclusive position bands: first named, second or third, fourth or later.
- A fixed, pre-named competitor set of two to four.
- Re-measure every four weeks by default.
- A competitor rotates in a cell if it appears in more than 10% and fewer than 90% of the cell's valid runs.
- An explicit refusal in text is a valid run; an empty body is a failed run.

The cell classes (never, rarely under 30%, flipping 30% to 70%, mostly, always) follow Kumar (2026), whose author works for a company that sells a visibility product.

## What the kit does not do

No composite score, no sentiment, no traffic or revenue figures, no exact-URL claims, no prompt rankings from small counts, no bands on share of voice. It measures; it does not explain why a brand is or is not named.
