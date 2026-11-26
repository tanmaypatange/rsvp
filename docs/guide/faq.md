# RSVP FAQ

**These are short answers to common questions about RSVP.**

Each answer points to the page with the detail. For the definition, see [What is RSVP?](what-is-rsvp.md)

## Does RSVP give a single score?

No. RSVP reports a **range** with a 95% band and the sample size. It has no composite score, because a single number hides which part moved. See [Share of voice](../framework/6-share-of-voice.md).

## How are the confidence bands computed?

As **95% Wilson intervals** for a proportion, for each rate, engine and declared location. See [Confidence bands](../framework/5-confidence-bands.md).

## What do informational, commercial and transactional mean?

- **Informational:** the buyer wants to learn or understand.
- **Commercial:** the buyer wants to compare or choose.
- **Transactional:** the buyer is ready to act or buy.

See [Prompt list and intent](prompt-list-and-intent.md).

## What counts as a mention?

The brand name, or an alias from a list you fixed before the first run, in the answer text. See [Mention](../framework/1-mention.md).

## What is a declared location?

A country, or a city for place-dependent questions, that you state for each run. It is declared, not observed. See [Engines and location](engines-and-location.md).

## How many competitors should you include?

Two to four. Name them before the first run and keep them fixed. See [Prompt list and intent](prompt-list-and-intent.md).

## Is three engines at 10 runs per prompt a minimum?

No. It is an example of the report format. Choose runs by the band width the decision needs. See [Runs and sample size](runs-and-sample-size.md).

## Can you get the visibility rate from the mention and citation rates?

Compute it from the run log. If you only have the mention and citation rates, it lies between the larger of the two and the smaller of 100% and their sum. See [Visibility rate](../framework/4-visibility-rate.md).

## Do the position bands overlap?

No. The bands are first named, second or third, and fourth or later, and their counts add up to the mentions. See [Position](../framework/3-position.md).

## Why six reporting rules?

The four rules in the overview are a subset of the six. See [Reporting Rules v0.1](../specifications/reporting-rules-v01.md).

## What should you do with a low rate?

Check the band, then the prompt list, then the pattern across measures. Then compare with competitors and re-measure. See [Reading results](reading-results.md).

## Does RSVP tell you why you are invisible?

No. RSVP measures. Treat any cause as a hypothesis and test it by re-measuring. See [Reading results](reading-results.md) and [Limitations](limitations.md).

## Does RSVP show the exact URLs an engine cited?

Not reliably. API answers only partly reproduce what an engine's web page cites at exact-URL level, so RSVP works at domain and brand level. See [Citation](../framework/2-citation.md).

## Does RSVP measure traffic?

No. Clicks, visits and sales are outside the method. See [Limitations](limitations.md).

## Are the numbers in the sample report real?

No. They are computed from the made-up Tidewater Ledger sample run to show the format. See [Sample report](../reports/sample-report.md).

Previous: What are the limitations of RSVP? | Next: Overview

Last updated: November 26, 2026
