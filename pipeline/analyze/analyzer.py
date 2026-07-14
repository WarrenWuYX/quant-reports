import json
from datetime import date

from . import prompts
from .schema import Analysis
from ..ingest.normalize import NormalizedDoc


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else ""
        if t.endswith("```"):
            t = t[:-3].strip()
    return t


class AnalysisError(Exception):
    pass


class Analyzer:
    def __init__(
        self,
        provider,
        taxonomy: dict,
        model: str = "GLM-5.2",
        max_attempts: int = 3,
        body_chars: int = 12000,
        extract_max_tokens: int = 3500,
        analyze_max_tokens: int = 7000,
    ):
        self.provider = provider
        self.tax = taxonomy
        self.model = model
        self.max_attempts = max(1, min(max_attempts, 3))
        self.body_chars = max(2000, body_chars)
        self.extract_max_tokens = extract_max_tokens
        self.analyze_max_tokens = analyze_max_tokens

    def analyze(self, doc: NormalizedDoc) -> Analysis:
        extracted = self._call_json([
            {"role": "system", "content": prompts.EXTRACT_SYSTEM},
            {"role": "user", "content": self._extract_prompt(doc)},
        ], max_tokens=self.extract_max_tokens)
        analyzed = self._call_json([
            {"role": "system", "content": prompts.ANALYZE_SYSTEM},
            {"role": "user", "content": self._analyze_prompt(doc, extracted)},
        ], max_tokens=self.analyze_max_tokens)
        return self._assemble(doc, extracted, analyzed)

    def _call_json(self, messages, max_tokens: int) -> dict:
        last = None
        last_error = None
        for attempt in range(self.max_attempts):
            # Most Ark chat models support JSON mode. The final attempt falls
            # back to prompt-constrained JSON for models that do not.
            mode = {"response_format": {"type": "json_object"}} if attempt < self.max_attempts - 1 else {}
            try:
                content = self.provider.chat(
                    messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    **mode,
                )
                last = content
                return json.loads(_strip_code_fence(content))
            except Exception as exc:
                last_error = exc
        detail = f"; last error: {type(last_error).__name__}: {last_error}" if last_error else ""
        raise AnalysisError(f"JSON parse failed after {self.max_attempts} attempts: {(last or '')[:200]}{detail}")

    def _extract_prompt(self, doc):
        return prompts.extract_user(
            title=doc.metadata.title, institution=doc.metadata.institution,
            body=doc.clean_text[:self.body_chars],
            research_type=self.tax.get("research_type", []),
            data_frequency=self.tax.get("data_frequency", []),
            factor_family=self.tax.get("factor_family", []),
            asset_class=self.tax.get("asset_class", []),
            method=self.tax.get("method", []),
        )

    def _analyze_prompt(self, doc, extracted):
        return prompts.analyze_user(
            title=doc.metadata.title, institution=doc.metadata.institution,
            body=doc.clean_text[:self.body_chars],
            extracted_json=json.dumps(extracted, ensure_ascii=False),
        )

    def _assemble(self, doc, extracted, analyzed) -> Analysis:
        detailed = analyzed.get("detailed", {})
        # merge extracted fields into detailed when LLM omits them
        if "performance" not in detailed:
            detailed["performance"] = extracted.get("performance", {"metrics": []})
        if "attribution" not in detailed:
            detailed["attribution"] = extracted.get("attribution", {"done": False, "summary": "未做"})
        if "novelty_assessment" not in detailed:
            detailed["novelty_assessment"] = {"type": "待定", "summary": ""}

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
            "detailed": detailed,
            "critical": analyzed.get("critical", {}),
            "entities": extracted.get("entities", []),
            "model_used": self.model,
        }
        return Analysis(**payload)
