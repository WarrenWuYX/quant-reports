import shutil
from pathlib import Path

from .registry.aggregator import save_all


def prepare_site_data(
    root: Path,
    analyses_dir: Path,
    registry_path: Path,
    landscape_path: Path,
) -> dict[str, int]:
    """Synchronize canonical analysis data into the Astro build inputs."""
    source_files = sorted(analyses_dir.glob("*.json"))
    if not source_files:
        raise RuntimeError(
            f"No analysis JSON files found in {analyses_dir}. "
            "Run the analysis pipeline before building the site."
        )

    site_root = root / "site"
    content_dir = site_root / "src" / "content" / "analyses"
    content_dir.mkdir(parents=True, exist_ok=True)

    source_names = {path.name for path in source_files}
    removed = 0
    for stale_path in content_dir.glob("*.json"):
        if stale_path.name not in source_names:
            stale_path.unlink()
            removed += 1

    for source_path in source_files:
        shutil.copy2(source_path, content_dir / source_path.name)

    save_all(analyses_dir, registry_path, landscape_path)

    data_dir = site_root / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(registry_path, data_dir / "entities.json")
    shutil.copy2(landscape_path, data_dir / "coverage.json")

    return {"copied": len(source_files), "removed": removed}
