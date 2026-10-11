# Synap institution index

Static, free "database" for the Synap app: tiny prefix-sharded JSON files served by GitHub Pages. The app fetches only the shard it needs.

## Contract (what the app calls)
- `GET {base}/meta.json` returns `{v, updated, count, shards, counts, sources[]}`. Show `updated` and the source credits in Settings.
- `GET {base}/index/{xx}.json`, where `xx` is the first 2 letters/digits (lowercase) of any word the student typed, returns `{"v":1,"p":"xx","items":[{id,n,s,d,t,u,k,a[]}]}`.
  `n` name, `s` state, `d` district, `t` type, `u` affiliating university, `k` kind (college/university/school), `a` aliases and acronyms.
- Each institution is indexed under the first 2 characters of every word of its name and of every alias, so "chandra", "scsvmv" and "viswa" all find the same record. The app filters the shard in memory. A 404 means no match. Cache shards on the device.

## Set up (once)
1. Create a public GitHub repo, upload this folder, then in Settings > Pages choose "Deploy from a branch", branch `main`, folder `/docs`.
2. Download the AISHE colleges and universities files from AIKosh yourself (follow the dataset page's terms) and save them as `data/raw/colleges.xlsx` and `data/raw/universities.xlsx`. Check the licence and fix `config/sources.json`.
3. Run the "Update institution index" workflow in the Actions tab. The app's base URL is `https://<you>.github.io/<repo>`.

## Notes
- Government column names vary. The script matches common headers (name, state, district, management/type, university, code). If a build says no header row was found, send the first rows of the file.
- `data/aliases.csv` holds hand-made acronyms, because automatic ones can't know that SCSVMV ends in "MV". Add rows as `official name,ALIAS1|ALIAS2`, with the name exactly as it appears in the data.
- A source's optional `url` makes the job fetch it politely (obeys robots.txt, 2 s delay, never overwrites on failure). Government sites may block bots, so manual download is the safe default.
- Safety guard: if a rebuild finds under half the previous count, it stops and keeps the old data.
- Schools are not included yet. Add a source with `"kind": "school"` once you've confirmed one that allows reuse.
