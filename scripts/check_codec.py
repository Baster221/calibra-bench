"""Check Python/JavaScript commitment encoding on synthetic Unicode inputs."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parents[1]
vectors = [
    {"protocol": "wire-check/v1", "text": "".join(chr(i) for i in range(4096)),
     "probabilities": [0, 1, 5000, 10000], "flags": [True, False, None]},
    {"questions": ["Caf\u00e9", "\u6d4b\u8bd5", "\U0001f680"],
     "reference": "\ud800x\udfff\u2028\u2029", "salt": "a" * 64,
     "nested": [{"z": 3, "a": "line\nquote\"backslash\\"}]},
]
node = """import {readFileSync} from 'node:fs';
import {canonical,digest} from './scripts/network.mjs';
const values=JSON.parse(readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(values.map(v=>({canonical:canonical(v),digest:digest(v)}))));"""
result = subprocess.run(["node", "--input-type=module", "-e", node],
                        cwd=root, input=json.dumps(vectors, ensure_ascii=True),
                        text=True, capture_output=True, check=True)
actual = json.loads(result.stdout)
for value, row in zip(vectors, actual, strict=True):
    expected = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert row["canonical"] == expected
    assert row["digest"] == hashlib.sha256(expected.encode()).hexdigest()
print("Python/JavaScript codec agrees on 4,096 code points, controls, astral and surrogate cases.")
