# Install and run the kit

[The RSVP kit](https://github.com/tanmaypatange/rsvp/) is a small Python command line. It runs a measurement, counts mentions and citations, computes the bands and writes the one-page report. You need Python 3.8 or later (tested on 3.13). There is nothing else to install: the kit uses only the standard library, including its HTTP client.

Five steps take you from the repository to a finished measurement. Start with the dry run, which needs no engine and no key.

## Step 1: Get the Kit

Clone the repository and move into it.

`git clone` `[https://github.com/tanmaypatange/rsvp.git](https://github.com/tanmaypatange/rsvp/)` `rsvp && cd rsvp`

## Step 2: Try the Dry Run First

`python3 rsvp.py dry-run`

The dry run uses the real runner, counter, reporter and run log on bundled fictional data, with a fake engine that returns canned answers. No engine is called and no key is needed. It writes measurements-dry-run/sample-tidewater-m1/report.md, which matches the sample report.

Tidewater Ledger example. The dry run measures a made-up brand, Tidewater Ledger, on three made-up engines. The files it matches are in the sample folder of the kit repository: sample_report.md ([view](https://github.com/tanmaypatange/rsvp/blob/main/sample/sample_report.md), [raw download](https://raw.githubusercontent.com/tanmaypatange/rsvp/main/sample/sample_report.md)), sample_runlog.jsonl ([view](https://github.com/tanmaypatange/rsvp/blob/main/sample/sample_runlog.jsonl), [raw download](https://raw.githubusercontent.com/tanmaypatange/rsvp/main/sample/sample_runlog.jsonl)) and sample_coded_runlog.csv ([view](https://github.com/tanmaypatange/rsvp/blob/main/sample/sample_coded_runlog.csv), [raw download](https://raw.githubusercontent.com/tanmaypatange/rsvp/main/sample/sample_coded_runlog.csv)).

## Step 3: Fill In the Config and the Prompt List

The config is the protocol you fix before the first run. Copy the two templates, then fill both in.

`cp config.example.yaml config.yaml`

`cp prompts.template prompts.yaml`

Every key is commented in config.example.yaml. The brand and aliases, the two to four competitors, the labelled prompts, the engines with their location method, the runs per prompt and the schedule days are the inputs described on the [Inputs page](inputs.md). Close the alias list before the first run. Changing the aliases, or anything else in the protocol, starts a new measurement ID, and runs of two measurement IDs are never mixed.

## Step 4: Add Your Engine Keys and Check the Config

Put your engine keys in keys.env, one NAME=value per line, using the names in key_env. The file is gitignored. Keys are never written to the run log or the report. The validate command also prints a notice, not an error, when the config has fewer than three or more than six engines, or fewer than four or more than eight unbranded prompts in an intent. These are working ranges, and the kit still runs outside them.

`python3 rsvp.py validate --config config.yaml`

## Step 5: Run

`python3 rsvp.py run --config config.yaml`

Each call runs the next scheduled day. Run the same command once a day until the plan is done. The report is written after the last run.

## What Does a Run Write?

Each measurement gets a folder under measurements/ named by its measurement ID. It holds manifest.json, protocol.json, plan.json, runlog.jsonl, changes.jsonl, deviations.jsonl, coded_runlog.csv and report.md. The run log is append only. A correction to the coding goes in changes.jsonl and the original rows are kept. The file measurements/index.jsonl lists every measurement ID with its config hash.

## How Do You Test the Kit?

`python3 -m unittest discover -s tests -t .`

The tests cover every counting and reporting rule the kit implements and an end-to-end dry run that must reproduce the sample report exactly.

See also: [Quickstart](quickstart.md), [Inputs](inputs.md), [Sample report](../reports/sample-report.md), [Reporting Rules v0.1](../specifications/reporting-rules-v01.md).

Previous: [How to Run Your First RSVP Measurement: The Quickstart](quickstart.md) | Next: [What does an RSVP measurement need as input?](inputs.md)

Last updated: November 27, 2026
