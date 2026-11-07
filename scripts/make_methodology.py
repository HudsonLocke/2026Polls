import csv, json, collections, datetime, os, textwrap

OUT="/Users/hudsonisonline/Desktop/Datasets"
rows=list(csv.DictReader(open(os.path.join(OUT,'all_polls_2026.csv'))))
pages=json.load(open('wiki_pages.json'))

def q(rs): return len({r['question_id'] for r in rs})
def firms(rs): return len({r['pollster'] for r in rs if r['pollster']})

by_src=collections.defaultdict(list); by_off=collections.defaultdict(list)
for r in rows:
    by_src[r['source']].append(r); by_off[r['office']].append(r)

dates=[r['end_date'] for r in rows if r['end_date']]
span=(min(dates), max(dates))
races=sorted({(r['office'], r['state'], r['district']) for r in rows if r['state']})
stages=collections.Counter(r['race_stage'] for r in rows)

top=sorted(((len({r['question_id'] for r in rs}), p) for p,rs in
            collections.defaultdict(list, {k:[x for x in rows if x['pollster']==k] for k in {r['pollster'] for r in rows}}).items()),
           reverse=True)[:30]

def table(pairs, w=46):
    return '\n'.join(f"      {k.ljust(w)} {v}" for k,v in pairs)

L=[]
A=L.append
A("="*78)
A("2026 U.S. MIDTERM POLLING DATASET  --  HOW THIS DATA WAS GATHERED")
A("="*78)
A("")
A(f"Compiled:            {datetime.datetime.now().strftime('%Y-%m-%d %H:%M %Z').strip()} (local time)")
A(f"Election day:        2026-11-03")
A(f"Folder:              {OUT}")
A(f"Candidate-level rows:{len(rows):>8,}")
A(f"Poll questions:      {q(rows):>8,}")
A(f"Distinct polling firms / consortia: {firms(rows):,}")
A(f"Field-date span (poll end dates):   {span[0]} to {span[1]}")
A(f"Distinct races covered:             {len(races):,}")
uniq=len({r['dedupe_key'] for r in rows})
A(f"Unique firm x race x end-date keys: {uniq:,}  (see DEDUPLICATION below)")
gen=[r for r in rows if r['race_stage'] in ('General','Special general')]
gq={r['question_id'] for r in gen}
withm={r['question_id'] for r in gen if r['margin_dem_minus_rep']}
A(f"General-election questions:         {len(gq):,}, of which {len(withm):,} carry a D-R margin")
flagged=sum(1 for r in rows if r['data_quality_flag'])
A(f"Rows carrying a data_quality_flag:  {flagged:,}  (see section 5)")
A("")
A("-"*78)
A("1. WHAT THIS IS")
A("-"*78)
A("")
A(textwrap.fill(
 "A compiled dataset of public opinion polls for the 2026 United States midterm "
 "elections, covering U.S. Senate races, gubernatorial races, U.S. House races "
 "(district-level), and the national congressional generic ballot. It includes the "
 "final pre-election polls released in the days before 3 November 2026 and the full "
 "earlier history each source carries, back to 2023 in places, so trend lines can be "
 "rebuilt from scratch. Primary-election and runoff polling is included and flagged, "
 "not dropped.", 78))
A("")
A(textwrap.fill(
 "The data is stored in long format: one row per candidate per poll question. A poll "
 "that asked two different matchups produces two question_ids; a matchup with four "
 "named candidates produces four rows under one question_id. "
 "poll_questions_2026.csv collapses that to one row per question if you want a "
 "wide-ish view.", 78))
A("")
A("-"*78)
A("2. SOURCES, AND WHY THESE ONES")
A("-"*78)
A("")
A(textwrap.fill(
 "FiveThirtyEight was the standard bulk source for raw poll data through 2024. It no "
 "longer exists: as of this compile, every URL under "
 "projects.fivethirtyeight.com/polls/data/ (senate_polls.csv, governor_polls.csv, "
 "house_polls.csv, generic_ballot_polls.csv) returns an HTTP 302 redirect chain that "
 "ends at abcnews.com/politics, serving HTML rather than CSV. The GitHub mirror "
 "fivethirtyeight/data no longer carries a polls/ directory for this cycle either. "
 "RealClearPolitics / RealClearPolling and 270toWin both return HTTP 403 to "
 "non-browser clients and publish no bulk export. Race to the WH publishes its poll "
 "list only through Infogram embeds whose stored payload was last updated in March "
 "2026 and contains no poll rows. So the three sources below are what is actually "
 "obtainable in bulk right now.", 78))
A("")
A("  SOURCE 1 -- VoteHub Polls API  (primary bulk source)")
A("  " + "-"*60)
A("      Endpoint:  https://api.votehub.com/polls")
A("      Format:    JSON array, one object per poll, nested 'answers' array")
A("      Auth:      none; free, no API key")
A("      Behaviour: returns the ENTIRE poll history on every call, all offices at")
A("                 once. Query parameters such as ?type=senate are accepted but")
A("                 ignored -- the response is byte-identical -- so the full file is")
A("                 downloaded once and split locally on the poll_type field.")
A("      License:   published as CC BY 4.0 by VoteHub.")
A("      Covers:    poll_type values us-senator, governor, us-representative,")
A("                 generic-ballot (also approval / favorability / primaries /")
A("                 attorney-general / mayor / propositions, which were not used).")
A(f"      Yield:     {q(by_src['VoteHub']):,} poll questions, {firms(by_src['VoteHub']):,} firms")
A("")
A("  SOURCE 2 -- Wikipedia per-race polling tables  (broadest firm coverage)")
A("  " + "-"*60)
A("      Endpoints: https://en.wikipedia.org/w/api.php          (page discovery)")
A("                 https://en.wikipedia.org/api/rest_v1/page/html/<title>")
A("      Format:    Parsoid HTML, parsed with BeautifulSoup + lxml")
A("      License:   text is CC BY-SA 4.0. Attribution required if redistributed.")
A(f"      Pages:     {len(pages)} candidate pages discovered, every page fetched")
A(f"      Yield:     {q(by_src['Wikipedia']):,} poll questions, {firms(by_src['Wikipedia']):,} firms")
A("      Why:       Wikipedia's race articles list campaign internals, state-level")
A("                 university polls, and small partisan shops that national")
A("                 aggregators skip, which is where most of the extra firm count")
A("                 comes from. It is also the only bulk-reachable source with")
A("                 primary and runoff polling at district level.")
A("")
A("  SOURCE 3 -- Silver Bulletin generic ballot database")
A("  " + "-"*60)
A("      Endpoint:  Google Sheets CSV export linked from")
A("                 https://www.natesilver.net/p/generic-ballot-average-2026-nate-")
A("                 silver-bulletin-congress-polls")
A("                 (docs.google.com/spreadsheets/d/e/2PACX-1vRsvXNCZ0ubJr8D_yNcU5")
A("                 q6C0_HBa35K7oDK03KpO7Ca43UwdXaIdvVLWoXEmHHph0EREz5430Hm5yZ/pub")
A("                 ?output=csv)")
A("      Format:    CSV, one row per generic-ballot poll")
A(f"      Yield:     {q(by_src['Silver Bulletin']):,} generic-ballot questions, "
  f"{firms(by_src['Silver Bulletin']):,} firms")
A("      Extra:     this source is the only one carrying house-effect-ADJUSTED")
A("                 numbers (adjusted_dem / adjusted_rep / adjusted_net) alongside")
A("                 the raw toplines, plus each poll's model weight and influence.")
A("                 Those columns are preserved in")
A("                 source_data/silver_bulletin_generic_ballot_with_adjusted.csv")
A("                 because the combined files only carry raw toplines.")
A("")
A("-"*78)
A("3. EXACTLY HOW IT WAS COLLECTED")
A("-"*78)
A("")
A("  Step 0 -- Source probe")
A("      curl -I over every candidate bulk endpoint to see what still responds with")
A("      data rather than HTML or a 403. This is what established that the")
A("      FiveThirtyEight CSVs are gone (see section 2).")
A("")
A("  Step 1 -- VoteHub")
A("      curl -L https://api.votehub.com/polls  ->  raw JSON saved verbatim.")
A("      Split on poll_type. The race is identified by the free-text 'subject'")
A("      field, which uses three shapes:")
A("          '2026 Ohio'              -> state race, general election")
art = None
A("          '2026 Texas Democratic'  -> state race, Democratic primary")
A("          '2026 AK-01'             -> House district")
A("          '2026'                   -> national generic ballot")
A("      These were parsed into separate state / district / race_stage columns.")
A("")
A("  Step 2 -- Wikipedia page discovery")
A("      Four methods were unioned so no race was missed because of a title")
A("      convention:")
A("          action=query&list=allpages&apprefix=...   for the predictable titles")
A("            ('2026 United States Senate election', '2026 United States House of")
A("             Representatives election', 'Opinion polling for the 2026', ...)")
A("          action=query&list=search&srsearch=intitle:...   for governor races,")
A("            which are titled '2026 <State> gubernatorial election', and for")
A("            'congressional district' special-election pages")
A("          action=query&prop=links   on the four hub pages (2026 United States")
A("            Senate elections / House of Representatives elections /")
A("            gubernatorial elections / elections)")
A("      The raw union was 260 pages. It was then filtered to U.S. federal and")
A("      U.S. governor races only. Two classes of false positive had to be removed:")
A("          - STATE legislatures. '2026 Alabama Senate election' and '2026 Alabama")
A("            House of Representatives election' are the state legislature, not")
A("            Congress. Only the 'United States Senate election in X' /")
A("            'United States House of Representatives election(s) in X' forms are")
art2=None
A("            federal.")
A("          - Foreign races. '2026 French Senate election', '2026 Bangkok")
A("            gubernatorial election', Russian oblast governorships, Nigerian state")
A("            governorships, Japanese prefectural governorships, Brazilian general")
A("            elections, and the Spanish / New Zealand polling pages all match the")
A("            same title patterns.")
A("      Governor pages were additionally checked against an explicit list of the 50")
A("      states, DC, and the five territories.")
A(f"      Result: {len(pages)} pages, listed in source_data/wikipedia_pages_used.txt.")
A("")
A("  Step 3 -- Wikipedia table parsing")
A("      Each page was fetched from the REST HTML endpoint and every <table> walked.")
A("      A table was treated as a polling table only if a header row within its")
A("      first six rows was mostly <th>, matched /poll source|pollster|poll|source/,")
A("      AND matched /date/. That rejects results tables, endorsement lists,")
A("      fundraising tables, and race-rating tables.")
A("      Mechanics that mattered:")
art3=None
A("          - rowspan / colspan. Wikipedia poll tables routinely rowspan the")
A("            pollster and date cells across several matchup rows. Every table was")
A("            expanded into a dense grid first, so a rowspanned pollster is carried")
A("            down to each matchup row instead of being read as blank.")
A("          - Column roles were assigned from the header text: pollster, date,")
A("            sample size, margin of error, sponsor, undecided, other, lead. Any")
A("            remaining non-empty, non-metadata header was treated as a candidate")
A("            column and melted into rows.")
A("          - <sup> elements were stripped and bracketed footnote markers removed")
A("            before reading any cell, so '47%[a]' parses as 47.0 and")
A("            'Emerson College[12]' as 'Emerson College'.")
A("          - Date strings were parsed from six observed shapes, including")
A("            'October 28-30, 2026', 'Oct 28 - Nov 1, 2026', '28-30 October 2026'")
A("            and bare single dates, with the year inferred from the page title")
A("            when the cell omitted it. A cross-month range whose end month is")
A("            earlier than its start month is rolled to the following year.")
A("          - The nearest preceding heading chain was recorded as wiki_section,")
A("            which is what supplies race_stage (General / Democratic primary /")
A("            Republican primary / Runoff / Special general) and, on multi-district")
A("            state pages, the district number.")
A("      Requests were rate-limited to roughly one per 1.1 seconds with a")
A("      descriptive User-Agent and exponential backoff on HTTP 429/503, after an")
A("      unthrottled first attempt was rate-limited. Every response was cached to")
A("      disk so the run is reproducible without re-hitting the API.")
A("")
A("  Step 4 -- Silver Bulletin")
A("      The article HTML was fetched and scanned for data links; it embeds a")
A("      published Google Sheets CSV export, which was downloaded directly.")
A("")
A("  Step 5 -- Normalisation")
A("      All three sources were mapped onto one schema (section 4). Specifically:")
A("          - State names were normalised both ways, because VoteHub mixes postal")
A("            codes ('AK', 'MI') and full names ('Alaska', 'Michigan') in the same")
A("            field. Both state and state_po are populated.")
A("          - Candidate party was taken from a trailing party suffix in the")
A("            candidate label where one existed: (D) (R) (I) (L) (G) (C) (NP)")
A("            (NPA) (WFP) (PSL) and others, plus 'Dem' / 'Rep' /")
A("            'Generic Democrat' style labels. Minnesota's DFL and North")
A("            Dakota's Democratic-NPL were mapped to D, since those are those")
A("            states' Democratic parties.")
A("          - Most sources do NOT label party at all -- VoteHub just gives bare")
A("            candidate names, and Wikipedia omits the suffix inside primary")
A("            tables. Party was therefore backfilled in three passes, each")
A("            recorded in data_quality_flag so you can audit or discard it:")
A("              1. party_inferred_from_name: a candidate who carries an explicit")
A("                 party label on SOME row gets that party on rows where the")
A("                 label is missing. Matched on a normalised name, scoped to the")
A("                 same state and office first, then globally for full names.")
A("              2. party_inferred_from_primary: in a Democratic or Republican")
A("                 primary poll, every candidate is of that party.")
A("              3. party_inferred_as_sole_opponent: in a general-election")
A("                 question with exactly two named candidates, where one is a")
A("                 known D or R and the other carries no party label ANYWHERE in")
A("                 the dataset, the second is assigned the opposite major party.")
A("                 This is the one inference that can be flatly wrong -- an")
A("                 unlabelled independent or nonpartisan candidate gets assigned")
A("                 D or R by it. It fired on a small number of rows; filter the")
A("                 flag out if that matters to you.")
A("          - Rows whose pollster cell parsed as a number, a percentage or a")
A("            sample-size string, and rows whose candidate was a table artefact")
A("            such as 'RCV round' in Alaska's ranked-choice tables, were dropped")
A("            as parser misalignment rather than kept as data.")
A("          - Pollster partisan lean: Wikipedia encodes it in the firm name")
A("            ('Cygnal (R)', 'Impact Research (D)'). That suffix was moved out of")
A("            the pollster name into pollster_partisan_lean so that 'Cygnal (R)'")
A("            and 'Cygnal' are the same firm, and internal_poll was set TRUE for")
A("            those rows. VoteHub and Silver Bulletin have their own partisan")
A("            fields, which were used as-is.")
A("          - dem_pct / rep_pct / margin_dem_minus_rep were computed per question")
A("            from the first Democratic and first Republican candidate in that")
A("            question, so two-way margins are directly usable.")
A("          - days_to_election = 2026-11-03 minus the poll's end date. Negative")
A("            values would mean post-election fieldwork; there are none.")
A("")
A("-"*78)
A("4. FILES")
A("-"*78)
A("")
A("  all_polls_2026.csv              every row, all offices, all sources")
A("  senate_polls_2026.csv           U.S. Senate only")
A("  governor_polls_2026.csv         governor only")
A("  house_polls_2026.csv            U.S. House, district-level")
A("  generic_ballot_polls_2026.csv   national congressional generic ballot")
A("  poll_questions_2026.csv         one row per poll question, with a")
A("                                  top_candidates summary string")
A("  pollsters_2026.csv              firm inventory: question counts by office,")
A("                                  which sources carry them, first and last poll")
A("  polling_aggregates_final_2026.csv")
A("                                  the final generic-ballot AVERAGES published by")
A("                                  the aggregators themselves (Decision Desk HQ,")
A("                                  FiftyPlusOne, NBC News, RealClearPolitics,")
A("                                  Silver Bulletin), as of 3 November 2026. These")
A("                                  are averages, not polls, and are kept in their")
A("                                  own file so they cannot be mistaken for polls.")
A("  HOW_THIS_DATA_WAS_GATHERED.txt  this file")
A("")
A("  source_data/")
A("    votehub_polls_long.csv                        VoteHub rows only")
A("    wikipedia_polls_long.csv                      Wikipedia rows only")
A("    silver_bulletin_generic_ballot_long.csv        Silver Bulletin rows only")
A("    silver_bulletin_generic_ballot_with_adjusted.csv")
A("                                                  raw + house-effect-adjusted")
A("    votehub_polls_raw.json                        unmodified API response")
A("    silver_bulletin_generic_ballot_raw.csv         unmodified sheet export")
A("    wikipedia_pages_used.txt                      the page list")
A("")
A("  Column dictionary for the combined files:")
A("")
cols=[("source","VoteHub | Wikipedia | Silver Bulletin"),
 ("office","Senate | Governor | House | Generic ballot"),
 ("cycle","election year the poll is about (2025 or 2026)"),
 ("state / state_po","full name and two-letter postal code"),
 ("district","House district number; blank for statewide and generic ballot"),
 ("race_label","e.g. 'Michigan Senate', 'OH-15', 'National generic ballot'"),
 ("race_stage","General | Democratic primary | Republican primary | Runoff |"),
 ("","  Democratic/Republican primary runoff | Special general | Primary"),
 ("poll_id / question_id","stable id for the poll question within this dataset"),
 ("pollster","firm or consortium, partisan suffix stripped"),
 ("pollster_partisan_lean","D | R | D/R | DEM | REP, blank if non-partisan"),
 ("sponsors","client or media sponsor where stated"),
 ("internal_poll","TRUE if campaign/party internal or partisan-sponsored"),
 ("start_date / end_date","ISO fieldwork dates"),
 ("field_dates_raw","the date string exactly as the source printed it"),
 ("days_to_election","2026-11-03 minus end_date"),
 ("sample_size","respondents"),
 ("population","lv = likely voters, rv = registered, a = adults, v = voters"),
 ("margin_of_error","reported MoE in points (Wikipedia rows mostly)"),
 ("candidate / candidate_party","name and party letter"),
 ("pct","that candidate's share in that question"),
 ("undecided_pct / other_pct","where the source broke them out"),
 ("dem_pct / rep_pct","first D and first R in the question, repeated on every"),
 ("","  row of that question"),
 ("margin_dem_minus_rep","dem_pct - rep_pct"),
 ("url","link to the poll release where the source carried one"),
 ("wiki_page / wiki_section","provenance for Wikipedia rows"),
 ("dedupe_key","office|state|district|stage|normalised pollster|end_date")]
for k,v in cols:
    A(f"      {k.ljust(24)} {v}")
A("")
A("-"*78)
A("5. THINGS YOU NEED TO KNOW BEFORE USING THIS")
A("-"*78)
A("")
import collections as _c
_keys=_c.Counter(r['dedupe_key'] for r in rows)
_bysrc=_c.defaultdict(set)
for r in rows: _bysrc[r['dedupe_key']].add(r['source'])
_cross=sum(1 for k,v in _bysrc.items() if len(v)>1)
A("DEDUPLICATION -- READ THIS BEFORE AVERAGING ANYTHING")
A("")
A(textwrap.fill(
 "SOURCES OVERLAP AND ARE NOT DEDUPLICATED. A poll carried by both VoteHub and "
 "Wikipedia appears twice, once per source. This is deliberate: the two records "
 f"often disagree on sample size, population or rounding, and silently picking a "
 f"winner would hide that. {_cross:,} dedupe_key values appear under more than one "
 f"source. Any average computed over these files without deduplicating will "
 "double-count.", 78))
A("")
A(textwrap.fill(
 "Deduplicate on dedupe_key, which is "
 "office|state_po|district|race_stage|normalised pollster|end_date. The pollster "
 "normalisation lowercases, strips a partisan suffix, strips a leading 'The' and "
 "strips punctuation, so 'The New York Times/Siena University' and "
 "'New York Times / Siena University' collapse to one firm. Simplest alternative: "
 "filter to a single source and ignore the rest.", 78))
A("")
A(textwrap.fill(
 "One nuance: a dedupe_key can legitimately cover several DIFFERENT questions, "
 "because one poll often asks more than one matchup (a head-to-head, then the same "
 "race with a third-party candidate added, then a primary). Those share firm, race "
 "and date but are not duplicates of each other. If you want one number per poll, "
 f"group by dedupe_key and pick a question deliberately -- the "
 f"{len(gq):,} general-election questions collapse to roughly "
 f"{len({r['dedupe_key'] for r in gen}):,} firm-race-date combinations.", 78))
A("")
_fabq=len({r['question_id'] for r in rows if 'pollster_admitted_fabrication' in r['data_quality_flag']})
_fabrows=sum(1 for r in rows if 'pollster_admitted_fabrication' in r['data_quality_flag'])
A("FABRICATED POLLS ARE PRESENT AND FLAGGED, NOT DELETED")
A("")
A(textwrap.fill(
 "2026 had a run of firms publishing invented numbers. Wedgewood Polls admitted on "
 "20 October 2026 that most of its results were made up, including its battleground "
 "surveys of Texas, Ohio, Michigan, Kansas and Maine; it called the exercise an "
 "experiment in how easily fake polling spreads. The New York Times pulled roughly "
 "15 of its surveys and Decision Desk HQ pulled 17 from its averages. Earlier, in "
 "August 2026, Median Strategies admitted its Los Angeles mayoral, Wisconsin and "
 "Nevada polls were fabricated and shut down. FiftyPlusOne has also suspended a "
 "separate firm over alleged falsified data in a Florida Republican gubernatorial "
 "primary survey.", 78))
A("")
A(textwrap.fill(
 f"Wedgewood Polls is still carried by VoteHub and so appears here: {_fabq} poll "
 f"questions, {_fabrows} candidate rows. Those rows were NOT deleted, because a "
 "silent deletion is worse than a labelled one -- you should be able to see what the "
 "aggregators were carrying. Every one is tagged "
 "'pollster_admitted_fabrication' in data_quality_flag. Exclude that flag before "
 "computing anything. Median Strategies produced no rows in these sources, so there "
 "is nothing to filter for it.", 78))
A("")
A(textwrap.fill(
 "That list is only the firms caught before this compile. Treat any unfamiliar "
 "pollster with no track record, no named principal and no published methodology as "
 "unverified -- that was the common signature in all three 2026 cases.", 78))
A("")
A(textwrap.fill(
 "PRIMARY AND GENERAL POLLING ARE MIXED IN THE SAME FILES, separated by race_stage. "
 "VoteHub in particular does not flag primaries in a dedicated field -- the only "
 "signal is the 'Democratic' / 'Republican' suffix on its subject string, which it "
 "uses inconsistently, so some primary polling may be labelled 'General'. "
 "Wikipedia's section headings are the more reliable stage signal. Filter "
 "race_stage == 'General' for general-election work.", 78))
A("")
A(textwrap.fill(
 "HOUSE COVERAGE IS SPARSE AND NON-RANDOM, in the data and in reality. Only "
 "competitive districts get polled, and most of what exists is campaign internals "
 "released because they were favourable. Treat district-level numbers, and any "
 "average of them, with much more suspicion than Senate or governor numbers.", 78))
A("")
A(textwrap.fill(
 "MARGIN OF ERROR IS MOSTLY EMPTY for VoteHub and Silver Bulletin rows, because "
 "neither source carries it. It is populated for most Wikipedia rows. Do not read a "
 "blank as 'no sampling error'.", 78))
A("")
A(textwrap.fill(
 "THE 'FINAL' POLLS ARE THE LAST ONES RELEASED, not a complete census of final "
 "polls. Firms that fielded through 2 November but released after the election, or "
 "never released, are absent. Late polling is also the most crowded with partisan "
 "releases.", 78))
A("")
A(textwrap.fill(
 "WIKIPEDIA ROWS ARE MACHINE-PARSED and carry the error rate of that. The parser "
 "was checked by hand against several race pages, but a header it did not recognise "
 "becomes a candidate column, and an unusual date string can fail to parse. "
 "wiki_page and wiki_section are on every row so any value can be traced back to "
 "the table it came from. Wikipedia itself is also a secondary source that anyone "
 "can edit.", 78))
A("")
A(textwrap.fill(
 "SOME CANDIDATE COLUMNS ARE NOT PEOPLE. 'Generic Democrat', 'Generic Republican', "
 "'Someone else' and similar appear as candidate values where a poll asked a generic "
 "matchup. They are kept, with blank or inferred party.", 78))
A("")
A(textwrap.fill(
 "PARTY LABELS ARE PARTLY INFERRED, and dem_pct / rep_pct / "
 "margin_dem_minus_rep are derived from them. Every inferred row says so in "
 "data_quality_flag (see section 3, step 5). The candidate and pct columns are "
 "always as the source gave them; the party and margin columns are the ones to "
 "distrust.", 78))
A("")
A(textwrap.fill(
 f"{len(gq)-len(withm):,} general-election questions carry no D-R margin, because "
 "no candidate in them could be identified as a Democrat or a Republican -- "
 "typically a poll of a jungle primary, an all-independent ballot test, or a "
 "matchup listing only one named candidate. The candidate-level rows are still "
 "there; only the convenience columns are blank.", 78))
A("")
A("-"*78)
A("6. WHAT IS IN THE DATA")
A("-"*78)
A("")
A("  By office (poll questions / candidate rows / distinct firms):")
A("")
for off in ['Senate','Governor','House','Generic ballot']:
    rs=by_off.get(off,[])
    if not rs: continue
    A(f"      {off.ljust(16)} {q(rs):>6,} questions   {len(rs):>6,} rows   {firms(rs):>4,} firms")
A("")
A("  By source (poll questions / candidate rows / distinct firms):")
A("")
for s in ['VoteHub','Wikipedia','Silver Bulletin']:
    rs=by_src.get(s,[])
    if not rs: continue
    A(f"      {s.ljust(16)} {q(rs):>6,} questions   {len(rs):>6,} rows   {firms(rs):>4,} firms")
A("")
A("  By race stage (candidate rows):")
A("")
for k,v in stages.most_common():
    A(f"      {k.ljust(30)} {v:>6,}")
A("")
A("  Poll end dates by year (candidate rows):")
A("")
yr=collections.Counter(r['end_date'][:4] for r in rows if r['end_date'])
for k in sorted(yr):
    A(f"      {k.ljust(30)} {yr[k]:>6,}")
A("")
A(f"  30 most prolific firms in this dataset (by poll questions, of {firms(rows):,} total):")
A("")
qc=collections.defaultdict(set)
for r in rows: qc[r['pollster']].add(r['question_id'])
for p,s in sorted(qc.items(), key=lambda kv:-len(kv[1]))[:30]:
    A(f"      {(p or '(blank)').ljust(46)} {len(s):>5,}")
A("")
A("  Senate races with polling in this dataset:")
A("")
sen=sorted({r['state'] for r in by_off.get('Senate',[]) if r['state']})
A(textwrap.fill(', '.join(sen), 74, initial_indent='      ', subsequent_indent='      '))
A("")
A("  Governor races with polling in this dataset:")
A("")
gov=sorted({r['state'] for r in by_off.get('Governor',[]) if r['state']})
A(textwrap.fill(', '.join(gov), 74, initial_indent='      ', subsequent_indent='      '))
A("")
A("  House districts with polling in this dataset:")
A("")
hd=sorted({f"{r['state_po']}-{r['district']}" for r in by_off.get('House',[]) if r['district']})
A(textwrap.fill(', '.join(hd), 74, initial_indent='      ', subsequent_indent='      '))
A("")
A("-"*78)
A("7. REPRODUCING / REFRESHING")
A("-"*78)
A("")
A("  VoteHub (whole history, one request):")
A("      curl -L 'https://api.votehub.com/polls' -o votehub_polls.json")
A("")
A("  Silver Bulletin generic ballot:")
A("      curl -L 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRsvXNCZ0ubJr8D_\\")
A("        yNcU5q6C0_HBa35K7oDK03KpO7Ca43UwdXaIdvVLWoXEmHHph0EREz5430Hm5yZ/pub?\\")
A("        output=csv' -o generic_ballot.csv")
A("")
A("  Wikipedia, one race page as HTML:")
A("      curl -H 'User-Agent: <your contact>' \\")
A("        'https://en.wikipedia.org/api/rest_v1/page/html/\\")
A("        2026_United_States_Senate_election_in_Michigan'")
A("")
A("  Wikipedia page discovery:")
A("      https://en.wikipedia.org/w/api.php?action=query&list=allpages\\")
A("        &apprefix=2026%20United%20States%20Senate%20election&aplimit=500\\")
A("        &apnamespace=0&format=json&formatversion=2")
A("      https://en.wikipedia.org/w/api.php?action=query&list=search\\")
A("        &srsearch=intitle:%222026%22%20intitle:%22gubernatorial%20election%22\\")
A("        &srlimit=500&srnamespace=0&format=json&formatversion=2")
A("")
A("  Python 3.14 with pandas / lxml / beautifulsoup4 in a venv was used for parsing;")
A("  only lxml and beautifulsoup4 are actually required.")
A("")
A("-"*78)
A("8. ATTRIBUTION")
A("-"*78)
A("")
A("  VoteHub poll data          CC BY 4.0 -- credit VoteHub")
A("  Wikipedia polling tables   CC BY-SA 4.0 -- credit Wikipedia contributors;")
A("                             share-alike applies if you redistribute")
A("  Silver Bulletin            Nate Silver / Silver Bulletin; check their terms")
A("                             before redistributing")
A("  Underlying polls remain the work of the individual polling firms named in the")
A("  pollster column.")
A("")
A("="*78)

open(os.path.join(OUT,'HOW_THIS_DATA_WAS_GATHERED.txt'),'w',encoding='utf-8').write('\n'.join(L)+'\n')
print("wrote HOW_THIS_DATA_WAS_GATHERED.txt", len('\n'.join(L)), "chars")
