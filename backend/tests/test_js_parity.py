"""The static demo builds pain sentences and word suggestions in the browser. These tests run the web app's
JavaScript (frontend/src/lib/pain.js, predict.js) with Node and check it gives exactly what the server gives."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from awaaz.pain import sentence, templates
from awaaz.predict import predict

ROOT = Path(__file__).resolve().parents[2]
LIB, DATA = ROOT / "frontend" / "src" / "lib", ROOT / "backend" / "awaaz" / "data"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")


def run_node(tmp_path: Path, module: str, script: str):
    for name in ("pain.json", "lexicon.json"):
        shutil.copy(DATA / name, tmp_path / name)
    src = (LIB / f"{module}.js").read_text(encoding="utf-8")
    src = src.replace('from "@data/pain.json";', 'from "./pain.json" with { type: "json" };')
    src = src.replace('from "@data/lexicon.json";', 'from "./lexicon.json" with { type: "json" };')
    (tmp_path / f"{module}.mjs").write_text(src, encoding="utf-8")
    (tmp_path / "run.mjs").write_text(script, encoding="utf-8")
    out = subprocess.run(["node", str(tmp_path / "run.mjs")], capture_output=True, timeout=60, check=True)
    return json.loads(out.stdout.decode("utf-8"))


def test_pain_sentences_match(tmp_path):
    js = run_node(tmp_path, "pain", """
import { PAIN, painSentence } from "./pain.mjs";
const out = [];
for (const lang of ["hi-IN", "ta-IN", "en-IN", "te-IN"]) for (const p of PAIN.parts) for (const side of p.sided ? ["left", "right"] : [null])
  for (const type of PAIN.types) for (const since of PAIN.since) for (let level = 0; level <= 10; level++)
    out.push(painSentence({ part: p.id, side, level, type, since, lang }));
process.stdout.write(JSON.stringify(out));
""")
    t = templates()
    py = [sentence(p["id"], lvl, kind, lang, side, since)
          for lang in ["hi-IN", "ta-IN", "en-IN", "te-IN"] for p in t["parts"]
          for side in (["left", "right"] if p["sided"] else [None])
          for kind in t["types"] for since in t["since"] for lvl in range(11)]
    assert len(py) == 17600 and js == py


CASES = [["", "en-IN", []], ["I n", "en-IN", []], ["please call my ", "en-IN", [["Please call my son Ravi", 4]]],
         ["mujhe p", "hi-IN", []], ["मुझे ", "hi-IN", [["मुझे पानी चाहिए", 5]]], ["ok please c", "en-IN", []],
         ["enakku", "ta-IN", []], ["I need wa", "te-IN", []], ["please bri", "en-IN", [["Please bring my glasses", 1], ["Please bring tea", 6]]],
         ["  I   NEED ", "en-IN", []], ["எனக்கு ", "ta-IN", []], ["कृपया ", "hi-IN", []], ["zzz", "en-IN", []],
         ["I need water", "en-IN", []], ["Thank", "en-IN", []], ["n", "hi-IN", []], ["en magana k", "ta-IN", []]]


def test_word_predictions_match(tmp_path):
    (tmp_path / "cases.json").write_text(json.dumps(CASES, ensure_ascii=False), encoding="utf-8")
    js = run_node(tmp_path, "predict", """
import { predict } from "./predict.mjs";
import { readFileSync } from "node:fs";
const cases = JSON.parse(readFileSync(new URL("./cases.json", import.meta.url), "utf8"));
process.stdout.write(JSON.stringify(cases.map(([t, l, h]) => predict(t, l, h))));
""")
    assert js == [predict(t, lang, [tuple(x) for x in h]) for t, lang, h in CASES]
