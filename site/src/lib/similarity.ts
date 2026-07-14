export interface SimilarityReport {
  slug: string;
  source: { title: string; institution: string };
  classification: Record<string, string[]>;
  entities?: Array<{ name: string; type: string }>;
  detailed?: { construction?: { type?: string | null } };
}

export interface SimilarityResult<T extends SimilarityReport = SimilarityReport> {
  report: T;
  score: number;
  reasons: string[];
}

const DIMENSIONS: Array<[string, number, string]> = [
  ["factor_family", 0.2, "因子"],
  ["method", 0.15, "方法"],
  ["research_type", 0.12, "研究类型"],
  ["data_frequency", 0.1, "频率"],
  ["asset_class", 0.08, "资产"],
  ["custom_tags", 0.05, "标签"],
];

function overlap(a: string[] = [], b: string[] = []) {
  const left = new Set(a.filter(Boolean));
  const right = new Set(b.filter(Boolean));
  const shared = [...left].filter((item) => right.has(item));
  const union = new Set([...left, ...right]);
  return {
    ratio: union.size === 0 ? 0 : shared.length / union.size,
    shared,
  };
}

function comparableEntities(report: SimilarityReport) {
  return (report.entities || [])
    .filter((entity) => entity.type === "factor" || entity.type === "method")
    .map((entity) => entity.name.trim())
    .filter(Boolean);
}

export function compareSimilarity<T extends SimilarityReport>(left: T, right: T) {
  let weighted = 0;
  const reasons: string[] = [];

  for (const [key, weight, label] of DIMENSIONS) {
    const result = overlap(left.classification?.[key], right.classification?.[key]);
    weighted += result.ratio * weight;
    if (result.shared.length) {
      reasons.push(`${label}：${result.shared.slice(0, 3).join("、")}`);
    }
  }

  const entityResult = overlap(comparableEntities(left), comparableEntities(right));
  weighted += entityResult.ratio * 0.25;
  if (entityResult.shared.length) {
    reasons.unshift(`共同实体：${entityResult.shared.slice(0, 3).join("、")}`);
  }

  const leftType = left.detailed?.construction?.type;
  const rightType = right.detailed?.construction?.type;
  if (leftType && rightType && leftType === rightType) {
    weighted += 0.05;
    reasons.push(`同为${leftType}构造`);
  }

  return {
    score: Math.min(100, Math.round(weighted * 100)),
    reasons: reasons.slice(0, 4),
  };
}

export function rankSimilar<T extends SimilarityReport>(base: T, reports: T[], limit = 8): SimilarityResult<T>[] {
  return reports
    .filter((report) => report.slug !== base.slug)
    .map((report) => ({ report, ...compareSimilarity(base, report) }))
    .sort((a, b) => b.score - a.score || a.report.source.title.localeCompare(b.report.source.title, "zh-CN"))
    .slice(0, limit);
}
