import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build
FX = pathlib.Path(__file__).resolve().parent / "fixtures"

class T(unittest.TestCase):
    def run_build(self, out):
        cfg = pathlib.Path(out) / "cfg.json"
        rel = str((FX / "colleges.csv").resolve().relative_to(build.ROOT))
        cfg.write_text(json.dumps({"sources": [{"id": "fx", "kind": "college", "file": rel}]}))
        return build.build(cfg, out, FX / "aliases.csv")
    def shard(self, out, p):
        with open(pathlib.Path(out) / "index" / f"{p}.json", encoding="utf-8") as f: return json.load(f)["items"]
    def test_alias_and_word_prefix_lookup(self):
        with tempfile.TemporaryDirectory() as out:
            meta = self.run_build(out); self.assertEqual(meta["count"], 2)
            self.assertTrue(any(i["n"].startswith("Test Sri") for i in self.shard(out, "ts")))
            self.assertTrue(any(i["n"].startswith("Test Sri") for i in self.shard(out, "vi")))
            self.assertEqual(self.shard(out, "du")[0]["n"], "Dummy College of Testing")
    def test_safety_guard_keeps_old_data(self):
        with tempfile.TemporaryDirectory() as out:
            self.run_build(out); m = pathlib.Path(out) / "meta.json"
            with open(m) as f: d = json.load(f)
            d["count"] = 100
            with open(m, "w") as f: json.dump(d, f)
            with self.assertRaises(SystemExit): self.run_build(out)
if __name__ == "__main__": unittest.main()
