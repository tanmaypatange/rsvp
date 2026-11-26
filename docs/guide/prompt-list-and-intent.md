# Prompt list and intent

**The prompt list is the market RSVP measures.**

Give each prompt one label: **informational** (the buyer wants to learn), **commercial** (the buyer wants to compare or choose) or **transactional** (the buyer is ready to act). Report results by intent, so no assumed traffic weighting is needed.

## How do you label prompts?

Give every prompt exactly one label, based on what the buyer wants.

- **Informational:** you could answer the question without naming a product.
- **Commercial:** you expect the answer to name products or providers.
- **Transactional:** the buyer wants to sign up, buy or start.

Five coding rules keep two analysts consistent.

- Use one label per prompt. If a prompt could be two, use the label of the buyer's final aim.
- Treat a comparison as commercial, even if no product is named.
- Treat an action verb about a kind of product (buy, sign up, start, set up, get) as transactional.
- Treat a prompt that can be answered without naming products as informational.
- Log disagreements. If more than one in ten labels differ, rewrite the rules before the measurement starts.

## Why these three labels?

The three-way split is a search-intent scheme from the keyword era. [Żatuchin and Dzemesjuk (2026](https://arxiv.org/abs/2608.30023)) label a corpus of simulated buyer prompts as informational, commercial, transactional or navigational, with navigational below 0.1%. They say the fit of this scheme to conversational traffic is an open question.

Drop the navigational label. A prompt that names the brand to find it is a **branded prompt**.

The label can matter for the sources an engine uses. A hotel study found that experiential queries produced 55.9% non-intermediary citations against 30.8% for transactional ones, on one platform ([Zhu and Chang, 2026](https://arxiv.org/abs/2603.20062)).

## Why is the headline list unbranded?

A prompt is **branded** if it names the client brand. Branded prompts measure whether an engine knows the brand. Unbranded prompts measure whether the engine brings the brand up on its own.

A study of 112 Product Hunt startups found that ChatGPT recognised a product by name in 99.4% of cases and Perplexity in 94.3%, but products appeared in 3.32% and 8.29% of discovery-style questions ([Sharma, 2025](https://arxiv.org/abs/2601.00912)).

Keep the headline list unbranded. Run branded prompts as a separate, labelled block.

**Tidewater Ledger example.** P10, Is Tidewater Ledger a good choice for a small bakery?, is the branded prompt and is reported apart. P06, which asks for alternatives to Quillmark Books, is unbranded and flagged competitor-named.

A prompt that names a competitor but not the client counts as unbranded. Flag it as competitor-named, because it invites a list that leaves the client out.

## How many prompts do you need?

RSVP fixes no number. A working range of **4 to 8 prompts per intent** gives usable per-intent results in a first measurement. [Schulte et al. (2026](https://arxiv.org/abs/2604.07585)) used eight prompts per vertical.

**Tidewater Ledger example.** The sample uses 3 prompts per intent, below this working range, so its per-intent bands are wide. On Engine A the informational mention rate is 3% (1 of 30, band 1 to 17) and the commercial rate is 30% (9 of 30, band 17 to 48).

Write each prompt as a buyer would, with the constraints a buyer would give, such as size, budget and region.

Do not count near-copies as separate evidence. [Martinez (2026b](https://arxiv.org/abs/2609.06811)) calls that pseudoreplication. Give paraphrases of one need a shared need ID and report them at the need level.

## Does the prompt list change the result?

Yes, strongly. [Kumar (2026](https://arxiv.org/abs/2606.20065)) found average visibility of 22.9% on broad discovery prompts and 74.6% on comparison prompts, and the comparison prompts named the brand in 46% of cases. Report the prompt list with every result and never leave it out.

## How do you choose the competitor set?

Pick **two to four competitors** with the client before the first run. Each one must be a rival the client would name and one that buyers' questions would plausibly produce.

Keep the set fixed. Fewer than two makes share of voice meaningless, and more than four clutters the report. Log other brands that engines name and list them with counts.

## Do you weight prompts by assumed traffic?

No. In the simulated corpus of [Żatuchin and Dzemesjuk (2026](https://arxiv.org/abs/2608.30023)) informational prompts made up 78.3%, commercial 17.4% and transactional 4.3%, but those shares come from simulated personas. Report intents separately so that no weighting is needed.

See also: [Inputs](inputs.md), [Mention](../framework/1-mention.md), [Share of voice](../framework/6-share-of-voice.md), [Reading results](reading-results.md).

Previous: [What does an RSVP measurement need as input?](inputs.md) | Next: [Engines and location](engines-and-location.md)

Last updated: November 26, 2026
