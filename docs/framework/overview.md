# Overview

Repeated Sampling of Visibility and Position (RSVP) measures how visible a brand is in AI search. It takes a brand, a competitor set and a list of buyer questions, runs every question many times on each AI engine, and reports visibility as a range with a confidence band rather than a single number.

It answers the question a client actually asks: when buyers ask an AI assistant about our category, do we come up, where in the answer, and how sure are we?

## Why repeated measurement

AI answers are noisy. The same question asked twice can produce different brand lists, and answers differ by engine and by the asker's location. A single check treats one draw from that noise as fact. RSVP treats each answer as one sample and measures the spread, so the result shows both the typical outcome and how much it moves.

## What it measures

- **Mention.** The brand is named anywhere in the answer text.
- **Citation.** The brand's domain is cited as a source.
- **Position.** Where the brand first appears in the answer: first named, second or third, or fourth or later.
- **Visibility rate.** The share of runs in which the brand is mentioned or cited, reported per engine with a confidence band.
- **Run spread.** How much the answer changes between repeated runs of the same question.

Results are always split by engine and by declared location. The main view is at the domain and brand level, because API runs only partly reproduce what an engine's web app cites at the exact-URL level.

## Inputs

- Brand name and domain.
- Competitor set.
- **Prompt list.** Buyer questions labelled informational, commercial or transactional. The prompt list defines the market being measured, so it is always reported alongside the results.
- Engines to test.
- Declared location or locations.
- Runs per prompt, the sample size.

## How it works

1. **Prompt builder.** Turns buyer intents into the prompt list, each prompt labelled by intent.
2. **Runner.** Loops over every combination of prompt, engine and run number, calling each engine's API with a declared location.
3. **Counter.** Counts mentions, citations and source domains in each run.
4. **Reporter.** Computes the rate and the interval per engine, then writes a one-page report: the visibility range, the per-engine and per-location split, and the run spread.

## Sample report

From the kit's sample report: the made-up brand Tidewater Ledger on three made-up engines, 10 runs per prompt, 300 planned runs, 296 valid, a pilot. The numbers are an example of the format, not real data.

| **Engine** | **Runs per prompt** | Mention rate | Citation rate | Position | Run spread |
|---|---|---|---|---|---|
| Engine A | 10 | 22% (15-32%) | 12% (7-21%) | First named in 5 of 20 mentions | 3 of 3 named competitors rotate in and out |
| Engine B | 10 | 16% (10-25%) | 14% (8-22%) | First named in 4 of 14 | 3 of 3 named competitors rotate in and out |
| Engine C | 10 | 58% (48-68%) | 40% (31-51%) | First named in 16 of 52 | Wide swings between runs (6 of 9 cells flipping); 3 of 3 named competitors rotate in and out |

## Reporting rules

- Report the range and the sample size, never a single number.
- Do not call a score share of voice without stating the prompt list behind it.
- Re-measure every few weeks. Engines change, and a measurement from last quarter is not a measurement of today.
- Keep the first sample small and say so. API costs grow with the number of runs.

## Current limitations

- API answers only partly reproduce what the web app cites at the exact-URL level, so claims stay at the domain and brand level.
- Location is declared, not observed.
- Small samples give wide bands. Treat early numbers as directional.

## Status and next steps

Early stage. The framework is being documented. The next step is a small automated workflow: it builds the prompt list from buyer intents, loops over every combination of prompt, engine and run number through each engine's API, counts mentions and citations, and writes the one-page report.
