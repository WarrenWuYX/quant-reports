import yaml
from . import io_paths


def load_config(path=None):
    path = path or io_paths.paths.config
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)