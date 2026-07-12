import json
from collections import defaultdict
from pathlib import Path


def _load_analyses(analyses_dir: Path) -> list[dict]:
    """Load all OK analysis JSONs from analyses_dir."""
    results = []
    for f in sorted(analyses_dir.glob("*.json")):
        d = json.loads(f.read_text("utf-8"))
        if d.get("status") == "ok":
            results.append(d)
    return results


def build_entities(analyses_dir: Path) -> dict:
    """Aggregate all factor and method entities across reports."""
    analyses = _load_analyses(analyses_dir)
    factor_map: dict[str, list[dict]] = defaultdict(list)
    method_map: dict[str, list[dict]] = defaultdict(list)

    for a in analyses:
        slug = a["slug"]
        title = a["source"]["title"]
        inst = a["source"]["institution"]
        tags = (
            a["classification"].get("research_type", [])
            + a["classification"].get("factor_family", [])
            + a["classification"].get("method", [])
        )
        for e in a.get("entities", []):
            ref = {"slug": slug, "title": title, "institution": inst}
            if e["type"] == "factor":
                factor_map[e["name"]].append(ref)
            elif e["type"] == "method":
                method_map[e["name"]].append(ref)

    factors = sorted(
        [{"name": k, "reports": v, "tags": _collect_tags(k, v, analyses), "report_count": len(v)}
         for k, v in factor_map.items()],
        key=lambda x: (-x["report_count"], x["name"])
    )
    methods = sorted(
        [{"name": k, "reports": v, "tags": _collect_tags(k, v, analyses), "report_count": len(v)}
         for k, v in method_map.items()],
        key=lambda x: (-x["report_count"], x["name"])
    )
    return {"factors": factors, "methods": methods}


def _collect_tags(name: str, refs: list[dict], analyses: list[dict]) -> list[str]:
    """Collect classification tags from all source reports of this entity."""
    slugs = {r["slug"] for r in refs}
    tags = set()
    for a in analyses:
        if a["slug"] in slugs:
            for key in ("research_type", "factor_family", "method", "asset_class"):
                for t in a["classification"].get(key, []):
                    tags.add(t)
    return sorted(tags)


def build_coverage(analyses_dir: Path) -> dict:
    """Build coverage matrices for landscape heatmap."""
    analyses = _load_analyses(analyses_dir)

    dimensions = [
        {"id": "factor_family_x_research_type", "label": "因子家族 × 研究类型",
         "x_axis": "research_type", "y_axis": "factor_family"},
        {"id": "asset_class_x_method", "label": "资产类别 × 方法",
         "x_axis": "method", "y_axis": "asset_class"},
        {"id": "factor_family_x_asset_class", "label": "因子家族 × 资产类别",
         "x_axis": "asset_class", "y_axis": "factor_family"},
    ]

    all_x_values: dict[str, set[str]] = {}
    all_y_values: dict[str, set[str]] = {}
    for dim in dimensions:
        xk, yk = dim["x_axis"], dim["y_axis"]
        all_x_values[xk] = set()
        all_y_values[yk] = set()
        for a in analyses:
            for v in a["classification"].get(xk, []):
                all_x_values[xk].add(v)
            for v in a["classification"].get(yk, []):
                all_y_values[yk].add(v)

    result_dims = []
    all_gaps = []

    for dim in dimensions:
        xk, yk = dim["x_axis"], dim["y_axis"]
        x_vals = sorted(all_x_values[xk])
        y_vals = sorted(all_y_values[yk])
        matrix = []
        for y in y_vals:
            for x in x_vals:
                slugs = []
                for a in analyses:
                    cls = a["classification"]
                    x_has = x in cls.get(xk, [])
                    y_has = y in cls.get(yk, [])
                    if x_has and y_has:
                        slugs.append(a["slug"])
                entry = {"x": x, "y": y, "count": len(slugs), "slugs": slugs}
                matrix.append(entry)
                if len(slugs) == 0:
                    all_gaps.append({"dimension": dim["id"], "x": x, "y": y, "count": 0})
        result_dims.append({"id": dim["id"], "label": dim["label"],
                           "x_axis": xk, "y_axis": yk,
                           "x_labels": x_vals, "y_labels": y_vals,
                           "matrix": matrix})

    return {"dimensions": result_dims, "gaps": all_gaps}


def save_all(analyses_dir: Path, registry_path: Path, landscape_path: Path) -> None:
    """Generate and save entities.json and coverage.json."""
    entities = build_entities(analyses_dir)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8")

    coverage = build_coverage(analyses_dir)
    landscape_path.parent.mkdir(parents=True, exist_ok=True)
    landscape_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")