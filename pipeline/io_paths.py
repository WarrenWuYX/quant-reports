from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ANALYSES = DATA / "analyses"
REGISTRY = DATA / "registry" / "entities.json"
LANDSCAPE = DATA / "landscape" / "coverage.json"
MANIFEST = DATA / "manifest.json"
CONFIG = ROOT / "config.yaml"


class _Paths:
    def __init__(self):
        self.root = ROOT
        self.data = DATA
        self.analyses = ANALYSES
        self.registry = REGISTRY
        self.landscape = LANDSCAPE
        self.manifest = MANIFEST
        self.config = CONFIG

    def vault(self, cfg):
        return Path(cfg["vault_path"])

    def clippings(self, cfg):
        return self.vault(cfg) / cfg["clippings_dir"]

    def pdfs(self, cfg):
        return self.vault(cfg) / cfg["pdfs_dir"]


paths = _Paths()