from pipeline.config import load_config
from pipeline import io_paths


def test_load_config_defaults():
    cfg = load_config()
    assert cfg["model"] == "GLM-5.2"
    assert cfg["vault_path"].endswith("obsidian")
    assert "research_type" in cfg["classification"]
    assert io_paths.paths.root.exists()
    assert io_paths.paths.analyses.name == "analyses"