import argparse
import subprocess
import sys
from pathlib import Path

from . import io_paths
from .analyze.analyzer import Analyzer
from .analyze.schema import Analysis
from .config import load_config
from .ingest.manifest import Manifest, SCHEMA_VERSION
from .ingest.markdown import parse_markdown_file
from .llm.provider import ArkProvider
from .publish import prepare_site_data
from .registry.aggregator import save_all


def _resolve_targets(cfg, args):
    clip = io_paths.paths.clippings(cfg)
    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = clip / args.file
        return [p]
    if args.slug:
        for md in sorted(clip.rglob("*.md")):
            if _is_hidden(md, clip):
                continue
            if parse_markdown_file(md, cfg).slug == args.slug:
                return [md]
        raise SystemExit(f"slug not found: {args.slug}")
    return [md for md in sorted(clip.rglob("*.md")) if not _is_hidden(md, clip)]


def _is_hidden(path: Path, base: Path) -> bool:
    """Check if any path component relative to base starts with '.'."""
    try:
        rel = path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return any(part.startswith(".") for part in rel.parts)


def _save(analysis: Analysis):
    out = io_paths.paths.analyses / f"{analysis.slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")


def _build_site() -> int:
    """Prepare canonical data and run the Astro production build."""
    site_root = io_paths.paths.root / "site"
    stats = prepare_site_data(
        root=io_paths.paths.root,
        analyses_dir=io_paths.paths.analyses,
        registry_path=io_paths.paths.registry,
        landscape_path=io_paths.paths.landscape,
    )
    print(f"Prepared {stats['copied']} analysis JSON(s); removed {stats['removed']} stale file(s)")
    print(f"Registry saved → {io_paths.paths.registry}")
    print(f"Landscape saved → {io_paths.paths.landscape}")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    result = subprocess.run([npm, "run", "build:astro"], cwd=str(site_root))
    if result.returncode != 0:
        print(f"npm run build failed with exit code {result.returncode}")
        return result.returncode

    dist = site_root / "dist"
    print(f"Site built → {dist}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    # run
    run = sub.add_parser("run")
    run.add_argument("--file")
    run.add_argument("--slug")
    run.add_argument("--no-build", action="store_true", help="Analyze only; skip registry and site build")
    # build
    build = sub.add_parser("build", help="Build the Astro static site")
    # registry
    reg = sub.add_parser("registry", help="Generate registry entities and landscape coverage JSON")
    sub.add_parser("prepare", help="Synchronize analysis and derived JSON into the Astro site")
    args = parser.parse_args(argv)

    if args.cmd == "registry":
        save_all(io_paths.paths.analyses, io_paths.paths.registry, io_paths.paths.landscape)
        print(f"Registry saved → {io_paths.paths.registry}")
        print(f"Landscape saved → {io_paths.paths.landscape}")
        return 0

    if args.cmd == "prepare":
        stats = prepare_site_data(
            root=io_paths.paths.root,
            analyses_dir=io_paths.paths.analyses,
            registry_path=io_paths.paths.registry,
            landscape_path=io_paths.paths.landscape,
        )
        print(f"Prepared {stats['copied']} analysis JSON(s); removed {stats['removed']} stale file(s)")
        return 0

    if args.cmd == "build":
        return _build_site()

    cfg = load_config()
    provider = ArkProvider(model=cfg["model"])
    manifest = Manifest.load(io_paths.paths.manifest)
    llm_cfg = cfg.get("llm", {})
    analyzer = Analyzer(
        provider,
        cfg["classification"],
        model=cfg["model"],
        max_attempts=llm_cfg.get("max_attempts", 3),
        body_chars=llm_cfg.get("body_chars", 12000),
        extract_max_tokens=llm_cfg.get("extract_max_tokens", 3500),
        analyze_max_tokens=llm_cfg.get("analyze_max_tokens", 7000),
    )

    clip = io_paths.paths.clippings(cfg)
    targets = _resolve_targets(cfg, args)
    changed = 0
    for path in targets:
        if not path.exists():
            continue
        rel = str(path.resolve().relative_to(clip.resolve())).replace("\\", "/")
        h = Manifest.hash_file(path)
        if not manifest.needs_analysis(rel, h, SCHEMA_VERSION):
            continue
        doc = parse_markdown_file(path, cfg)
        try:
            analysis = analyzer.analyze(doc)
        except Exception as e:
            print(f"[FAIL] {rel}: {e}")
            continue
        _save(analysis)
        manifest.update(rel, h, SCHEMA_VERSION)
        changed += 1
        print(f"[OK] {rel} -> {analysis.slug}.json")
    manifest.save(io_paths.paths.manifest)
    print(f"analyzed {changed} report(s); {len(targets)} scanned")
    usage = getattr(provider, "usage_totals", None)
    if usage and usage.get("total_tokens"):
        print(
            "Ark usage: "
            f"input={usage['prompt_tokens']}, output={usage['completion_tokens']}, "
            f"total={usage['total_tokens']} tokens"
        )
    return 0 if args.no_build else _build_site()


if __name__ == "__main__":
    raise SystemExit(main())
