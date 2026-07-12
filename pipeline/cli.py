import argparse
import shutil
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
            if parse_markdown_file(md, cfg).slug == args.slug:
                return [md]
        raise SystemExit(f"slug not found: {args.slug}")
    return sorted(clip.rglob("*.md"))


def _save(analysis: Analysis):
    out = io_paths.paths.analyses / f"{analysis.slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")


def _build_site() -> int:
    """Copy analysis JSONs into Astro content dir, generate registry, and run astro build."""
    site_root = io_paths.paths.root / "site"
    content_dir = site_root / "src" / "content" / "analyses"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Copy all JSONs from data/analyses to site content directory
    copied = 0
    for json_path in sorted(io_paths.paths.analyses.glob("*.json")):
        dst = content_dir / json_path.name
        shutil.copy2(json_path, dst)
        copied += 1
    print(f"Copied {copied} analysis JSON(s) to {content_dir}")

    # Step 2: Generate registry + landscape JSONs
    from .registry.aggregator import save_all
    save_all(io_paths.paths.analyses, io_paths.paths.registry, io_paths.paths.landscape)
    print(f"Registry saved → {io_paths.paths.registry}")
    print(f"Landscape saved → {io_paths.paths.landscape}")

    # Step 3: Copy registry/landscape JSONs into site src/data dir
    data_dir = site_root / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(io_paths.paths.registry, data_dir / "entities.json")
    shutil.copy2(io_paths.paths.landscape, data_dir / "coverage.json")

    # Step 4: Run npm run build
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    result = subprocess.run([npm, "run", "build"], cwd=str(site_root))
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
    # build
    build = sub.add_parser("build", help="Build the Astro static site")
    # registry
    reg = sub.add_parser("registry", help="Generate registry entities and landscape coverage JSON")
    args = parser.parse_args(argv)

    if args.cmd == "registry":
        save_all(io_paths.paths.analyses, io_paths.paths.registry, io_paths.paths.landscape)
        print(f"Registry saved → {io_paths.paths.registry}")
        print(f"Landscape saved → {io_paths.paths.landscape}")
        return 0

    if args.cmd == "build":
        return _build_site()

    cfg = load_config()
    provider = ArkProvider(model=cfg["model"])
    manifest = Manifest.load(io_paths.paths.manifest)
    analyzer = Analyzer(provider, cfg["classification"], model=cfg["model"])

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
