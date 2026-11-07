Scripts that produced this dataset, in run order.

Requirements:  python3  +  beautifulsoup4  lxml
    python3 -m venv .venv && .venv/bin/pip install beautifulsoup4 lxml

Run order (from this scripts/ directory; they write into ../ and ./raw, ./cache):

    1.  curl -L 'https://api.votehub.com/polls' -o raw/votehub_polls.json
    2.  curl -L '<Silver Bulletin sheet URL in HOW_THIS_DATA_WAS_GATHERED.txt>' \
            -o raw/silverbulletin_generic_ballot.csv
    3.  python discover.py          -> wiki_candidates.json   (260 pages)
    4.  python filter_pages.py      -> wiki_pages.json        (160 pages)
    5.  python parse_wiki.py        -> wiki_rows.json         (~3,700 poll questions)
    6.  python aggregates.py        -> polling_aggregates_final_2026.csv
    7.  python normalize.py         -> the combined CSVs
    8.  python dedupe.py            -> ../deduped/*.csv
    9.  python mkt_kalshi_inventory.py -> raw/mkt/kalshi_inventory.json
   10.  python mkt_kalshi_history.py   -> raw/mkt/kalshi_history.json
   11.  python mkt_pm_inventory.py     -> raw/mkt/pm_inventory.json   (slow: searches
                                          Polymarket once per race)
   12.  python mkt_pm_history.py       -> raw/mkt/pm_history.json
   13.  python mkt_join.py             -> adds the 13 odds columns to every poll file
   14.  python build_race_level.py   -> ../analysis/race_level_2026.csv
   15.  python make_methodology.py  -> HOW_THIS_DATA_WAS_GATHERED.txt

mktlib.py is the shared Kalshi/Polymarket client (same caching + backoff idea as
wikilib.py, cache in ./cache_mkt). mkt_join.py REWRITES the poll CSVs in place,
appending the odds columns, so it is idempotent and safe to re-run.

wikilib.py is the shared Wikipedia client: 1.1 s minimum between requests,
exponential backoff on HTTP 429/503, and an on-disk gzip cache in ./cache so a
re-run costs no API calls. Set a contact address in its UA constant before
re-running against Wikipedia.

dedupe.py reads ../all_polls_2026.csv and writes ../deduped/. Run it after
normalize.py and before make_methodology.py, which reports on both sets.

normalize.py and dedupe.py write to the absolute path in its OUT constant - change that if you
move the folder.
