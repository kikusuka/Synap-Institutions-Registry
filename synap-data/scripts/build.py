#!/usr/bin/env python3
"""Build prefix-sharded institution index files for the Synap app (static, GitHub Pages friendly)."""
import csv, json, re, sys, shutil, hashlib, datetime, pathlib, argparse, time
import urllib.request, urllib.robotparser, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
STOP = {"of", "and", "the", "for", "in", "a", "an"}
UA = "SynapDataBot/1.0 (education data; contact: set-in-README)"
# header aliases (matched against normalised header text); first hit wins
H = {
    "name": ["collegename", "institutionname", "institutename", "nameofthecollege", "nameoftheinstitution", "name", "universityname"],
    "state": ["state"], "district": ["district"],
    "type": ["management", "collegetype", "institutiontype", "type"],
    "univ": ["affiliatinguniversity", "affiliateduniversity", "universityname", "university"],
    "code": ["aishecode", "code", "id"],
}

def norm(s):
    s = str(s or "").lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

def hkey(s): return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

def map_headers(headers):
    keys = [hkey(h) for h in headers]; out = {}
    for field, aliases in H.items():
        for a in aliases:
            if a in keys and keys.index(a) not in out.values():
                out[field] = keys.index(a); break
    return out

def read_rows(path):
    path = pathlib.Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        with open(path, newline="", encoding="utf-8-sig") as f: rows = list(csv.reader(f))
    for i, r in enumerate(rows):  # first row that looks like a header (has a name column)
        m = map_headers(r)
        if "name" in m and len(m) >= 2:
            return m, rows[i + 1:]
    raise SystemExit(f"No header row with a name column found in {path}")

def load_aliases(path):
    out = {}
    p = pathlib.Path(path)
    if not p.exists(): return out
    with open(p, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[norm(r["match_name"])] = [a.strip().lower() for a in r["aliases"].split("|") if a.strip()]
    return out

def fetch(url, dest):
    """Polite fetch: obeys robots.txt, identifies itself, never overwrites on failure."""
    u = urllib.parse.urlparse(url)
    rp = urllib.robotparser.RobotFileParser(f"{u.scheme}://{u.netloc}/robots.txt")
    try: rp.read()
    except Exception: pass
    if not rp.can_fetch(UA, url): print(f"robots.txt disallows {url}; skipping"); return False
    time.sleep(2)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r: data = r.read()
    with open(dest, "wb") as f: f.write(data)
    return True

def record(row, m, kind, aliases):
    g = lambda k: str(row[m[k]]).strip() if k in m and m[k] < len(row) and row[m[k]] is not None else ""
    name = g("name")
    if len(name) < 3: return None
    toks = [t for t in norm(name).split() if t not in STOP and len(t) >= 2]
    acr = "".join(t[0] for t in toks) if len(toks) >= 2 else ""
    al = set(aliases.get(norm(name), []))
    if acr: al.add(acr)
    code = g("code")
    rid = code or hashlib.sha1((norm(name) + norm(g("state"))).encode()).hexdigest()[:10]
    rec = {"id": rid, "n": name, "s": g("state"), "d": g("district"), "t": g("type"), "u": g("univ"), "k": kind, "a": sorted(al)}
    pfx = {t[:2] for t in toks} | {a[:2] for a in al if len(a) >= 2}
    return rec, pfx

def build(config, out_dir, aliases_path, force=False):
    with open(config, encoding="utf-8") as f: cfg = json.load(f)
    out = pathlib.Path(out_dir); aliases = load_aliases(aliases_path)
    shards, seen, counts = {}, set(), {}
    for src in cfg["sources"]:
        fp = ROOT / src["file"]
        if src.get("url"):
            fp.parent.mkdir(parents=True, exist_ok=True)
            try: fetch(src["url"], fp)
            except Exception as e: print(f"fetch failed for {src['id']}: {e}")
        if not fp.exists(): print(f"missing {fp}; skipping {src['id']}"); continue
        m, rows = read_rows(fp); n = 0
        for row in rows:
            r = record(row, m, src["kind"], aliases)
            if not r or r[0]["id"] in seen: continue
            seen.add(r[0]["id"]); n += 1
            for p in r[1]: shards.setdefault(p, []).append(r[0])
        counts[src["id"]] = n
    total = sum(counts.values())
    meta_p = out / "meta.json"
    old = 0
    if meta_p.exists():
        with open(meta_p, encoding="utf-8") as f: old = json.load(f)["count"]
    if total == 0 or (old and total < 0.5 * old and not force):
        sys.exit(f"Safety stop: parsed {total} institutions vs {old} before. Keeping old data (use --force to override).")
    idx = out / "index"
    if idx.exists(): shutil.rmtree(idx)
    idx.mkdir(parents=True)
    for p, items in shards.items():
        with open(idx / f"{p}.json", "w", encoding="utf-8") as f:
            json.dump({"v": 1, "p": p, "items": items}, f, ensure_ascii=False, separators=(",", ":"))
    meta = {"v": 1, "updated": datetime.date.today().isoformat(), "count": total, "shards": len(shards), "counts": counts,
            "sources": [{k: s.get(k) for k in ("id", "kind", "source_name", "source_url", "license")} for s in cfg["sources"]]}
    with open(meta_p, "w", encoding="utf-8") as f: json.dump(meta, f, indent=1)
    print(f"Built {total} institutions into {len(shards)} shards")
    return meta

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config/sources.json"))
    ap.add_argument("--out", default=str(ROOT / "docs"))
    ap.add_argument("--aliases", default=str(ROOT / "data/aliases.csv"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(); build(a.config, a.out, a.aliases, a.force)
