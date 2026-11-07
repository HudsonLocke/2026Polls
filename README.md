# 2026 U.S. Midterm Polling + Prediction-Market Dataset

Public polling for the 2026 United States midterm elections — U.S. Senate, governor,
U.S. House (district level) and the national congressional generic ballot — with the
Kalshi and Polymarket win probabilities for each race attached to every poll, averaged
over the days that poll was in the field.

| | |
|---|---|
| Candidate-level rows | 15,764 |
| Poll questions | 6,273 |
| Distinct polling firms | 490 |
| Field dates (poll end dates) | 2022-07-10 to 2026-11-02 |
| Races covered | 267 |
| Deduplicated questions | 5,314 |
| Race-level analysis rows | 205 |
| Compiled | 2026-11-07 |

Election day was **3 November 2026**. The latest poll in the set ended 2 November 2026.

## Start here

- **`deduped/all_polls_2026_deduped.csv`** — the file most people want. One record per
  poll question, sources merged, odds attached.
- **`analysis/race_level_2026.csv`** — one row per race: final polling average, each
  platform's eve-of-election probability, and the realised winner.
- **`HOW_THIS_DATA_WAS_GATHERED.txt`** — full provenance, methodology and caveats.
  Read section 5 before computing anything.

## Layout

```
all_polls_2026.csv                every poll row, all sources, NOT deduplicated
senate_polls_2026.csv             one file per office
governor_polls_2026.csv
house_polls_2026.csv
generic_ballot_polls_2026.csv
poll_questions_2026.csv           one row per poll question
pollsters_2026.csv                firm inventory with counts and date ranges
polling_aggregates_final_2026.csv the aggregators' own final generic-ballot averages

deduped/                          same files, one record per question (see below)
analysis/race_level_2026.csv      race-level file for winner-accuracy analysis
source_data/                      per-source extracts + unmodified raw payloads
scripts/                          every script that produced this, in run order
HOW_THIS_DATA_WAS_GATHERED.txt    methodology
```

## Sources

FiveThirtyEight's bulk poll CSVs no longer exist — every URL under
`projects.fivethirtyeight.com/polls/data/` now redirects to `abcnews.com/politics`.
RealClearPolitics and 270toWin return HTTP 403 to non-browser clients and publish no
bulk export. This dataset is therefore built from sources that are actually obtainable
in bulk:

| Source | What it gives | Licence |
|---|---|---|
| [VoteHub](https://votehub.com) Polls API | 1,878 poll questions, all offices | CC BY 4.0 |
| Wikipedia race articles (160 pages) | 3,709 poll questions, widest firm coverage | CC BY-SA 4.0 |
| [Silver Bulletin](https://www.natesilver.net) | 690 generic-ballot polls, incl. house-effect-adjusted | see their terms |
| [Kalshi](https://kalshi.com) elections API | daily contract prices per race | see their terms |
| [Polymarket](https://polymarket.com) Gamma + CLOB | daily contract prices per race | see their terms |

Wikipedia supplies most of the long tail — campaign internals, university polls and
small partisan shops that national aggregators skip. It is also the only bulk-reachable
source carrying margin of error and undecided shares.

## Deduplication

The top-level files are **not** deduplicated: a poll carried by two sources appears
twice, because the records often disagree on sample size, population or rounding and
silently picking a winner would hide that. `deduped/` resolves it by *merging* rather
than picking — the sources are complementary, so Wikipedia supplies margin of error and
undecided while VoteHub supplies the poll URL and sponsor. Of 6,273 questions,
959 were cross-source duplicates; on the merged records 785 of 959 agree to the
decimal. Methodology section 9 has the matching rules.

## Prediction-market odds

Every general-election poll carries both platforms' probability that each party wins
that race, averaged over the poll's fieldwork window: 2,573 of 4,742
general-election questions have Kalshi odds (54%), 3,500 have Polymarket odds
(74%), and 3,917 have at least one (83%).

The two platforms were matched to races through entirely separate logic, and where both
cover a question their Democratic win probability agrees to a **median of 1.2
probability points** — a useful check that the race matching and window averaging are
sound.

**These odds are not independent of the polls.** Markets move partly in response to
published polling, including the polls in this dataset. Reading the market number as
outside confirmation of the poll beside it is circular.

## Known issues, in brief

- **Fabricated polls are present and flagged, not deleted.** Wedgewood Polls admitted on
  20 October 2026 that most of its results were invented; VoteHub still carried 11 of its
  questions. Every one is tagged `pollster_admitted_fabrication` in `data_quality_flag`.
- **Party labels are partly inferred** and so are the derived `dem_pct` / `rep_pct` /
  margin columns. `candidate` and `pct` are always verbatim from the source; each
  inference names its rule in `data_quality_flag`.
- **Kalshi's two legs do not always sum to 1** — each party is a separate binary, so a
  thin market can price both sides high at once. Use `kalshi_dem_prob_norm`.
- **The generic ballot is matched to House *control*,** not vote share. Different quantity.
- **House polling is sparse and non-random.** Only competitive districts get polled, and
  much of what exists is campaign internals released because they were favourable.

Full detail, including the merge bugs that were found and fixed, is in
`HOW_THIS_DATA_WAS_GATHERED.txt`.

## Reproducing

```bash
python3 -m venv .venv && .venv/bin/pip install beautifulsoup4 lxml
cd scripts && cat README.txt      # scripts run in numbered order
```

## Attribution

Underlying polls remain the work of the individual polling firms named in the `pollster`
column. Wikipedia-derived rows are CC BY-SA 4.0; VoteHub-derived rows are CC BY 4.0.
Check Kalshi's, Polymarket's and Silver Bulletin's terms before redistributing their data.
