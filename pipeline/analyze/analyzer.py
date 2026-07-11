import json
from datetime import date

from . import prompts
from .schema import Analysis
from ..ingest.normalize import NormalizedDoc


class AnalysisError(Exception):
    pass


class Analyzer:
    MAX_RETRIES = 3
    BODY_TRUNC = 12000

    def __init__(self, provider, taxonomy: dict, model: str = "GLM-5.2"):
        self.provider = provider
        self.tax = taxonomy
        self.model = model

    def analyze(self, doc: NormalizedDoc) -> Analysis:
        extracted = self._call_json([
            {"role": "system", "content": prompts.EXTRACT_SYSTEM},
            {"role": "user", "content": self._extract_prompt(doc)},
        ])
        analyzed = self._call_json([
            {"role": "system", "content": prompts.ANALYZE_SYSTEM},
            {"role": "user", "content": self._analyze_prompt(doc, extracted)},
        ])
        return self._assemble(doc, extracted, analyzed)

    def _call_json(self, messages) -> dict:
        last = None
        for mode in ({"response_format": {"type": "json_object"}}, {}):
            for _ in range(self.MAX_RETRIES):
                content = self.provider.chat(messages, **mode)
                last = content
                try:
                    return json.loads(content)
                except Exception:
                    continue
        raise AnalysisError(f"JSON parse failed: {(last or '')[:200]}")

    def _extract_prompt(self, doc):
        return prompts.extract_user(
            title=doc.metadata.title, institution=doc.metadata.institution,
            body=doc.clean_text[:self.BODY_TRUNC],
            research_type=self.tax.get("research_type", []),
            data_frequency=self.tax.get("data_frequency", []),
            factor_family=self.tax.get("factor_family", []),
            asset_class=self.tax.get("asset_class", []),
            method=self.tax.get("method", []),
        )

    def _analyze_prompt(self, doc, extracted):
        return prompts.analyze_user(
            title=doc.metadata.title, institution=doc.metadata.institution,
            body=doc.clean_text[:self.BODY_TRUNC],
            extracted_json=json.dumps(extracted, ensure_ascii=False),
        )

    def _assemble(self, doc, extracted, analyzed) -> Analysis:
        payload = {
            "slug": doc.slug,
            "source": {
                "title": doc.metadata.title, "institution": doc.metadata.institution,
                "authors": doc.metadata.authors, "published": doc.metadata.published,
                "source_type": doc.source_type, "original_url": doc.metadata.original_url,
                "local_path": doc.source_path, "ingested_at": str(date.today()),
            },
            "classification": extracted.get("classification", {}),
            "ratings": extracted.get("ratings", {"quality": 3, "novelty": 3, "reusability": 3}),
            "concise": analyzed.get("concise", {}),
            "detailed": analyzed.get("detailed", {}),
            "critical": analyzed.get("critical", {}),
            "entities": extracted.get("entities", []),
            "model_used": self.model,
        }
        return Analysis(**payload)