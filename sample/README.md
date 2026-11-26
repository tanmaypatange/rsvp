# Sample files

Everything in this folder was made by `python3 rsvp.py dry-run`. The dry run uses a fake engine that returns canned answers for a made-up brand, Tidewater Ledger. Every brand, engine, answer and number is fictional. None of it measures a real product or engine.

The three files show one measurement at three stages: what the runner stores, what the counter adds, and what the reporter writes.

| File | Stage | What it is |
| --- | --- | --- |
| `sample_runlog.jsonl` | 1. Raw run log | The runner's output. One JSON row per run, 300 rows. It holds the engine and its details, the declared location and how it was passed, the prompt text sent, the times, the status, the full answer text and the cited links. It holds no counts, no mention flags and no rates. It is append only and is never edited. |
| `sample_coded_runlog.csv` | 2. Coded run log | The counter's output. Still one row per run, 300 rows. Each run is marked valid or failed, with the brands named in order, mention, cited, ghost citation, position and band, competitors named and cited domains. |
| `sample_report.md` | 3. Report | The reporter's output. Every count, rate and 95% Wilson band in it is computed from the coded rows. It is the report a client reads. |

## How they connect

1. The runner sends each prompt to each engine with the declared location, many times, and writes one row per answer to the raw run log.
2. The counter reads each answer under the fixed counting rules and writes the coded run log. A correction goes into a separate change list and never over the original row.
3. The reporter reads the coded rows and fills the report template. It refuses to write the report when a reporting rule has an empty slot, when the log is incomplete, or when the log mixes setups.

Example: the report's headline row for Engine A shows a visibility rate of 28% (25 of 89). Count the Engine A rows in the coded log that are valid and have `mention` or `cited` set to 1, over the valid Engine A rows for that location, and you get the same 25 of 89.

The log has 300 planned runs. 296 are valid and 4 failed (2 errors, 1 timeout, 1 empty body). The report's Inputs section states the same numbers. A refusal stays a valid run.

## Rebuild them

```
python3 rsvp.py dry-run
```

This writes the same three files under `measurements-dry-run/`. The test suite runs the dry run and checks that the output is byte-identical to the files here. To refresh them after a deliberate change, run `python3 rsvp.py dry-run --write-sample`.

The other files in this folder are inputs to the dry run: `config.sample.yaml`, `canned_answers.json` and `redirects.json`.
