import hashlib
import json
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = "1.0"


class Manifest:
    def __init__(self, files=None):
        self.files: dict = files or {}

    @staticmethod
    def load(path) -> "Manifest":
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return Manifest(data.get("files", {}))
        return Manifest()

    @staticmethod
    def hash_file(path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def needs_analysis(self, source_path, content_hash, schema_version=SCHEMA_VERSION) -> bool:
        entry = self.files.get(source_path)
        if not entry:
            return True
        return entry.get("hash") != content_hash or entry.get("schema_version") != schema_version

    def update(self, source_path, content_hash, schema_version=SCHEMA_VERSION, analyzed_at=None):
        self.files[source_path] = {
            "hash": content_hash,
            "schema_version": schema_version,
            "analyzed_at": analyzed_at or datetime.utcnow().isoformat(),
        }

    def save(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"files": self.files}, ensure_ascii=False, indent=2), encoding="utf-8")