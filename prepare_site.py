"""Build hook used by the Astro project to prepare generated site data."""

from pipeline import io_paths
from pipeline.publish import prepare_site_data


def main() -> int:
    stats = prepare_site_data(
        root=io_paths.paths.root,
        analyses_dir=io_paths.paths.analyses,
        registry_path=io_paths.paths.registry,
        landscape_path=io_paths.paths.landscape,
    )
    print(
        f"Prepared site data: {stats['copied']} analysis JSON(s), "
        f"{stats['removed']} stale file(s) removed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
