"""Offline source/deployment integrity check; online check is npm run verify."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "deployment.json").read_text())
source = (root / manifest["source_path"]).read_bytes()
digest = hashlib.sha256(source).hexdigest()
assert digest == manifest["source_sha256"] == manifest["deployed_source_sha256"]
assert manifest["byte_for_byte_match"] is True
assert manifest["deployment_status"] == "FINALIZED"
assert manifest["deployment_execution"] == "SUCCESS"
assert manifest["runner"] in source.decode().splitlines()[0]
print("Local source matches verified deployment manifest:", digest)
