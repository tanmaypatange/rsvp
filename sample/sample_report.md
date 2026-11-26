# RSVP report: Tidewater Ledger

**Illustrative.** Every brand, engine, answer and number in this report is made up. It was produced by the dry run on canned answers to show the format. It is not a measurement of any real product or engine.

**Measurement sample-tidewater-m1.** Measured 2026-11-02 to 2026-11-06, 5 days with runs (dates of the calls, UTC).

**Rule check.** Each reporting rule has a fixed slot below. The reporter refuses to write a report with an empty slot.

| Check | Slot |
|---|---|
| Rule 1: every rate with its count and a 95% band | filled |
| Rule 2: split by engine and declared location, no pooled headline | filled |
| Rule 3: prompt list attached, with intent labels | filled |
| Rule 3: share of voice states prompts, engines, location, runs and denominator | filled |
| Rule 4: date of this measurement | filled |
| Rule 4: date of the next measurement | filled |
| Rule 5: first sample marked as a pilot where it is one | filled |
| Rule 6: directional wording where bands are wide | filled |
| All rules: limits section present | filled |

## 1. Inputs

- **Brand:** Tidewater Ledger (tidewaterledger.example). Aliases: Tidewater, TidewaterLedger. Exclusions: Tidewater Capital.
- **Named competitors (3, fixed before the first run):** Quillmark Books (quillmarkbooks.example), Harrow Accounts (harrowaccounts.example), Saltbox Books (saltboxbooks.example).
- **Other brands tracked for order only:** Penfold Pay, Corvid Cash, Larkspur Tax.
- **Declared locations:** United States. **Network location:** fixed test network, United States (fictional).
- **Engines:**
  - Engine A: adapter fake, model engine-a-model-1, mode search-on, interface api. Location passed by the engine's location setting.
  - Engine B: adapter fake, model engine-b-model-1, mode search-on, interface api. Location passed by a sentence at the start of the prompt ("I am in {location}.").
  - Engine C: adapter fake, model engine-c-model-1, mode search-on, interface api. Location passed by the engine's location setting.
- **Runs:** 10 per prompt per engine and location, over 5 scheduled days. 300 planned, 296 valid, 4 failed and excluded.
- **Prompts:** 9 unbranded (3 informational, 3 commercial, 3 transactional); 1 branded, reported apart.

**Prompt list (rule 3).** This list is the market measured. Every result below is for this list only.

| ID | Need | Intent | Flags | Prompt |
|---|---|---|---|---|
| P01 | N01 | informational |  | How should a two-person design studio keep its books without hiring an accountant? |
| P02 | N02 | informational |  | What records does a sole trader need to keep for quarterly tax payments? |
| P03 | N03 | informational |  | What is the difference between bookkeeping and accounting for a small shop? |
| P04 | N04 | commercial |  | Which accounting software suits a freelance photographer who invoices in two currencies? |
| P05 | N04 | commercial |  | Best bookkeeping app for a freelancer billing clients in euros and dollars |
| P06 | N05 | commercial | competitor-named | What are good alternatives to Quillmark Books for a small charity? |
| P07 | N06 | transactional |  | Sign up for an invoicing app with a free trial for my cleaning business |
| P08 | N07 | transactional |  | Set up accounting software for a new online store today, which should I start with? |
| P09 | N08 | transactional |  | Buy a bookkeeping subscription for a five-person consultancy |
| P10 | N09 | commercial | branded | Is Tidewater Ledger a good choice for a small bakery? |

## 2. Headline: visibility rate per engine and declared location (rules 1 and 2)

Every figure is split by engine and by declared location. No figure is pooled across engines or locations. Engines: Engine A, Engine B, Engine C. Declared locations: United States.

| Engine | Declared location | Valid runs | Visibility rate | Mention rate | Citation rate | Band width |
|---|---|---|---|---|---|---|
| Engine A | United States | 89 | 28% (25 of 89), band 20 to 38 | 22% (20 of 89), band 15 to 32 | 12% (11 of 89), band 7 to 21 | within 20 points |
| Engine B | United States | 88 | 27% (24 of 88), band 19 to 37 | 16% (14 of 88), band 10 to 25 | 14% (12 of 88), band 8 to 22 | within 20 points |
| Engine C | United States | 89 | 71% (63 of 89), band 61 to 79 | 58% (52 of 89), band 48 to 68 | 40% (36 of 89), band 31 to 51 | within 20 points |

Visibility rate: valid runs with a mention or a citation, divided by valid runs. Failed runs are left out of every denominator. Runs with no citations stay in. Bands are 95% Wilson intervals, in percent.

## 3. Mention rate by intent

| Engine | Declared location | Intent | Mention rate |
|---|---|---|---|
| Engine A | United States | informational | 3% (1 of 30), band 1 to 17 |
| Engine A | United States | commercial | 30% (9 of 30), band 17 to 48 |
| Engine A | United States | transactional | 34% (10 of 29), band 20 to 53 |
| Engine B | United States | informational | not observed in 29 runs (band 0 to 12) |
| Engine B | United States | commercial | 27% (8 of 30), band 14 to 44 |
| Engine B | United States | transactional | 21% (6 of 29), band 10 to 38 |
| Engine C | United States | informational | 31% (9 of 29), band 17 to 49 |
| Engine C | United States | commercial | 67% (20 of 30), band 49 to 81 |
| Engine C | United States | transactional | 77% (23 of 30), band 59 to 88 |

Rates are not weighted by any assumed share of traffic. Each intent is reported on its own.

## 4. Citation and ghost citations

| Engine | Declared location | Valid runs | Mentioned and cited | Mentioned, not cited | Cited, not mentioned (ghost) | Neither | Runs with no citations |
|---|---|---|---|---|---|---|---|
| Engine A | United States | 89 | 6 | 14 | 5 | 64 | 17 |
| Engine B | United States | 88 | 2 | 12 | 10 | 64 | 35 |
| Engine C | United States | 89 | 25 | 27 | 11 | 26 | 4 |

Citation matches the brand's registrable domain, subdomains included, after tracking parameters are stripped and redirects resolved. A ghost citation counts toward the citation and visibility rates, not the mention rate. A citation shows presence among the sources, not endorsement.

- Engine A, United States: most cited domains, in runs out of 89 valid: smallbizdesk.example (28), bookkeepingweekly.example (24), shopkeeper.example (22), taxbasics.example (21), startupnotes.example (19).
- Engine B, United States: most cited domains, in runs out of 88 valid: freelancehub.example (17), startupnotes.example (16), bookkeepingweekly.example (15), shopkeeper.example (15), smallbizdesk.example (14).
- Engine C, United States: most cited domains, in runs out of 89 valid: tidewaterledger.example (36), freelancehub.example (30), taxbasics.example (27), shopkeeper.example (25), smallbizdesk.example (25).

## 5. Position when mentioned

| Engine | Declared location | Mentions | 1st named | 2nd or 3rd | 4th or later |
|---|---|---|---|---|---|
| Engine A | United States | 20 | 5 (25%) | 13 (65%) | 2 (10%) |
| Engine B | United States | 14 | 4 (29%) | 9 (64%) | 1 (7%) |
| Engine C | United States | 52 | 16 (31%) | 29 (56%) | 7 (13%) |

Counted only for runs with a mention. Each mention falls in exactly one band, so the three counts sum to the mentions. Text order stands in for prominence; it does not measure attention.

## 6. Share of voice (rule 3)

Share of voice is client mentions divided by client plus named-competitor mentions, over the same runs, one count per brand per run. It is for the 9 unbranded prompts listed in section 1 (P01, P02, P03, P04, P05, P06, P07, P08, P09), the engines and declared locations shown, at 10 runs per prompt. It is descriptive: counts only, no band. It is not market share.

| Engine | Declared location | Client mentions | Named-competitor mentions (3 named) | Share of voice |
|---|---|---|---|---|
| Engine A | United States | 20 | 115 | 14.8% (20 of 135 brand mentions) |
| Engine B | United States | 14 | 118 | 10.6% (14 of 132 brand mentions) |
| Engine C | United States | 52 | 110 | 32.1% (52 of 162 brand mentions) |

Runs naming each brand, with the share of valid runs:

| Engine | Declared location | Tidewater Ledger | Quillmark Books | Harrow Accounts | Saltbox Books |
|---|---|---|---|---|---|
| Engine A | United States | 20 (22%) | 55 (62%) | 38 (43%) | 22 (25%) |
| Engine B | United States | 14 (16%) | 54 (61%) | 36 (41%) | 28 (32%) |
| Engine C | United States | 52 (58%) | 52 (58%) | 40 (45%) | 18 (20%) |

Other brands named (not in share of voice; found from the tracked list only, so an approximation): Engine A, United States: Penfold Pay 21, Corvid Cash 20, Larkspur Tax 16; Engine B, United States: Penfold Pay 23, Larkspur Tax 22, Corvid Cash 19; Engine C, United States: Larkspur Tax 35, Corvid Cash 25, Penfold Pay 16.

## 7. Run spread

| Engine | Declared location | Never | Rarely | Flipping | Mostly | Always | Brand overlap | Domain overlap |
|---|---|---|---|---|---|---|---|---|
| Engine A | United States | 2 | 3 | 4 | 0 | 0 | 0.22 | 0.11 |
| Engine B | United States | 4 | 2 | 3 | 0 | 0 | 0.25 | 0.06 |
| Engine C | United States | 0 | 1 | 6 | 2 | 0 | 0.31 | 0.15 |

A cell is one prompt on one engine and declared location, classed by its mention rate: never 0%, rarely under 30%, flipping 30% to 70%, mostly over 70% and under 100%, always 100%. With few runs a cell's class is itself noisy. Overlap is the mean Jaccard index over every pair of valid runs in a cell (pairs where both sets are empty are skipped), then the mean over cells; 1.00 means identical sets. A competitor rotates in a cell when it appears in more than 10% and fewer than 90% of the cell's valid runs.

- **Engine A, United States:** 3 of 3 named competitors rotate in and out (Harrow Accounts in 8 of 9 cells, Quillmark Books in 8 of 9 cells, Saltbox Books in 6 of 9 cells); the brand's position band shifts between runs of the same prompt.
- **Engine B, United States:** 3 of 3 named competitors rotate in and out (Harrow Accounts in 8 of 9 cells, Quillmark Books in 8 of 9 cells, Saltbox Books in 7 of 9 cells); the brand's position band shifts between runs of the same prompt.
- **Engine C, United States:** wide swings between runs (6 of 9 cells flipping); 3 of 3 named competitors rotate in and out (Harrow Accounts in 9 of 9 cells, Quillmark Books in 7 of 9 cells, Saltbox Books in 5 of 9 cells); the brand's position band shifts between runs of the same prompt.

**Day by day (mention rate):**

| Date | Engine A, United States | Engine B, United States | Engine C, United States |
|---|---|---|---|
| 2026-11-02 | 18% (3 of 17), band 6 to 41 | 17% (3 of 18), band 6 to 39 | 67% (12 of 18), band 44 to 84 |
| 2026-11-03 | 11% (2 of 18), band 3 to 33 | 6% (1 of 17), band 1 to 27 | 44% (8 of 18), band 25 to 66 |
| 2026-11-04 | 28% (5 of 18), band 12 to 51 | 6% (1 of 18), band 1 to 26 | 67% (12 of 18), band 44 to 84 |
| 2026-11-05 | 22% (4 of 18), band 9 to 45 | 29% (5 of 17), band 13 to 53 | 56% (10 of 18), band 34 to 75 |
| 2026-11-06 | 33% (6 of 18), band 16 to 56 | 22% (4 of 18), band 9 to 45 | 59% (10 of 17), band 36 to 78 |

Each day holds fewer runs than the whole measurement, so each day's band is wider. A change seen on a single day is noise, not a result.

## 8. Reading

- **Engines, visibility rate, United States, on this prompt list and these dates:** Engine C above Engine A: bands do not overlap; Engine C above Engine B: bands do not overlap; Engine A and Engine B: bands overlap, no difference shown.
- **Intent:** the lowest mention rate is on informational prompts for 3 of 3 engine and location pairs. A low rate on prompts that do not call for a product is not by itself a problem.
- **Ghost citations:** Engine A, United States: 5 ghost citations next to 20 mentions; Engine B, United States: 10 ghost citations next to 14 mentions; Engine C, United States: 11 ghost citations next to 52 mentions.
- **Drift (mention rate, first and last day):** Engine A, United States: 18% on 2026-11-02, 33% on 2026-11-06; bands overlap, no change shown; Engine B, United States: 17% on 2026-11-02, 22% on 2026-11-06; bands overlap, no change shown; Engine C, United States: 67% on 2026-11-02, 59% on 2026-11-06; bands overlap, no change shown. A single day proves nothing; a move that holds across the days is a reason to measure again sooner.
- RSVP measures and does not explain. Any suspected cause is a hypothesis: write it down, change one thing, and re-measure with the same inputs.

## 9. Pilot and directional wording (rules 5 and 6)

**PILOT.** This measurement is a pilot: 10 runs per prompt is at or below the pilot threshold of 10; it is the first measurement under this protocol. It is kept small on purpose, because cost grows with prompts times engines times runs times locations. Add runs where a result is close to a decision.

**DIRECTIONAL.** Read every number in this report as direction only, not as a firm level: the sample is a pilot. With few runs the bands are wide.

## 10. Limits

1. Answers fetched through an API match what the engine's own web page cites only in part, so this report speaks about brands and domains, never about a particular page.
2. The location was stated to each engine, not observed. Engines differ in whether they use the stated location or the network the call came from; the network location is given in section 1.
3. Few runs mean wide bands. The band formula assumes independent runs; runs of different prompts share a brand and a market, so the true uncertainty is a little larger than shown.
4. Each band covers run-to-run noise for this prompt list only. It does not cover the choice of prompts or drift after these dates.
5. This report gives no reason why the brand is or is not named, no forecast of what any change would do, and no figure for traffic, clicks, revenue, tone or accuracy.
6. 56 of 266 valid unbranded runs showed no citations; they are valid outcomes and stay in every denominator.
7. Serving model changed during the measurement: Engine A served engine-a-model-1, engine-a-model-2.

## 11. Next measurement (rule 4)

**Next measurement: 2026-12-04**, 4 weeks after the last run, with the same inputs (prompt list, alias list, competitor set, engines, declared location and how it is passed). Measure again sooner if you learn that an engine changed. These results hold for the dates above only.

## Method note

- **Measurement ID:** sample-tidewater-m1. **Config hash:** ed4c7e51b7d83709. **Kit release:** 0.1.1. **Method:** RSVP v0.1.
- **Run status:** ok 294, refused 2, error 2, empty 1, timeout 1. Error, empty and timeout are failed runs and are excluded. A refusal in text is a valid run with no mention.
- **Retries:** 6 runs needed more than one attempt (technical failures only, at most three attempts).
- **Battery mention rate** (mean of per-prompt rates, equal weight per prompt) against the pooled rate used in the headline: Engine A, United States: battery 22.5%, pooled 22.5%; Engine B, United States: battery 15.8%, pooled 15.9%; Engine C, United States: battery 58.4%, pooled 58.4%.
- **Branded block** (P10; measures whether the engine knows the brand, kept out of every figure above): mention rate Engine A, United States: 90% (9 of 10), band 60 to 98; Engine B, United States: 80% (8 of 10), band 49 to 94; Engine C, United States: 100% (10 of 10), band 72 to 100.
- **Second-analyst recode:** not done yet. Write the sample with `python3 rsvp.py recode-sample`, have a second analyst fill it without seeing the coding, then run `python3 rsvp.py agreement`. Report agreement before release.
- **Corrections applied from the change list:** 0 (originals kept in the run log).
- **Deviations:** none logged.

## Appendix: prompt-level counts

| Prompt | Need | Intent | Engine A, United States | Engine B, United States | Engine C, United States |
|---|---|---|---|---|---|
| P01 | N01 | informational | 0/10 | 0/10 | 5/9 |
| P02 | N02 | informational | 1/10 | 0/10 | 3/10 |
| P03 | N03 | informational | 0/10 | 0/9 | 1/10 |
| P04 | N04 | commercial | 3/10 | 3/10 | 6/10 |
| P05 | N04 | commercial | 3/10 | 3/10 | 8/10 |
| P06 | N05 | commercial | 3/10 | 2/10 | 6/10 |
| P07 | N06 | transactional | 2/9 | 0/10 | 9/10 |
| P08 | N07 | transactional | 2/10 | 2/9 | 7/10 |
| P09 | N08 | transactional | 6/10 | 4/10 | 7/10 |

Mentions out of valid runs. Counts only, with no bands, listed in prompt order and not ranked: each cell holds too few runs for a band that could separate prompts.

**By need.** Paraphrases of one buyer need share a need ID and are read together, not as separate evidence:

| Need | Prompts | Engine A, United States | Engine B, United States | Engine C, United States |
|---|---|---|---|---|
| N01 | P01 | 0/10 | 0/10 | 5/9 |
| N02 | P02 | 1/10 | 0/10 | 3/10 |
| N03 | P03 | 0/10 | 0/9 | 1/10 |
| N04 | P04, P05 | 6/20 | 6/20 | 14/20 |
| N05 | P06 | 3/10 | 2/10 | 6/10 |
| N06 | P07 | 2/9 | 0/10 | 9/10 |
| N07 | P08 | 2/10 | 2/9 | 7/10 |
| N08 | P09 | 6/10 | 4/10 | 7/10 |
