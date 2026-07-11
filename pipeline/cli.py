import argparse
from pathlib import Path

from . import io_paths
from .analyze.analyzer import Analyzer
from .analyze.schema import Analysis
from .config import load_config
from .ingest.manifest import Manifest, SCHEMA_VERSION
from .ingest.markdown import parse_markdown_file
from .llm.provider import ArkProvider


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--file")
    run.add_argument("--slug")
    args = parser.parse_args(argv)

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
