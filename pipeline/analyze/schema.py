from typing import Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    institution: str
    authors: list[str] = []
    published: Optional[str] = None
    source_type: str
    original_url: Optional[str] = None
    local_path: str
    ingested_at: str


class Classification(BaseModel):
    research_type: list[str] = []
    data_frequency: list[str] = []
    factor_family: list[str] = []
    asset_class: list[str] = []
    method: list[str] = []
    custom_tags: list[str] = []


class Ratings(BaseModel):
    quality: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    reusability: int = Field(ge=1, le=5)


class Concise(BaseModel):
    one_liner: str
    core_points: list[str] = []
    key_result: str


class Metric(BaseModel):
    name: str
    value: str


class Performance(BaseModel):
    metrics: list[Metric] = []
    benchmark: Optional[str] = None
    backtest_period: Optional[str] = None
    turnover: Optional[str] = None
    capacity: Optional[str] = None
    ic_decay: Optional[str] = None
    summary: str = ""


class Attribution(BaseModel):
    done: bool
    method: Optional[str] = None
    summary: str
    gap: Optional[str] = None


class Construction(BaseModel):
    type: str  # factor | model | strategy | config
    data_inputs: list[dict] = []
    backtest_setup: Optional[dict] = None
    combination: Optional[str] = None
    parameters: list[dict] = []
    factor_definition: Optional[str] = None
    processing_pipeline: list[str] = []
    model_architecture: Optional[str] = None
    inputs: list[str] = []
    outputs: Optional[str] = None
    training: Optional[str] = None
    strategy_logic: Optional[str] = None
    allocation: Optional[str] = None


class Robustness(BaseModel):
    subsample_stability: Optional[str] = None
    style_bias: Optional[str] = None
    turnover: Optional[str] = None
    capacity: Optional[str] = None
    summary: str = ""


class DataDependency(BaseModel):
    data_required: str = ""
    reproducibility: str = ""
    summary: str = ""


class PriorArt(BaseModel):
    method: str
    relation: str = ""


class NoveltyAssessment(BaseModel):
    type: str
    summary: str


class Detailed(BaseModel):
    core_content: str
    economic_logic: str
    construction: Construction
    excess_return_logic: str
    performance: Performance
    attribution: Attribution
    robustness: Robustness = Robustness()
    data_dependency: DataDependency = DataDependency()
    prior_art: list[PriorArt] = []
    novelty_assessment: NoveltyAssessment


class ImprovementIdea(BaseModel):
    idea: str
    based_on: str = ""
    expected_gain: str = ""


class Critical(BaseModel):
    weaknesses: list[str] = []
    useful_elements: list[str] = []
    inspirations: list[str] = []
    improvement_ideas: list[ImprovementIdea] = []
    replication_plan: str = ""


class Entity(BaseModel):
    name: str
    type: str


class RelatedReport(BaseModel):
    slug: str
    title: str
    relation: str = ""


class Analysis(BaseModel):
    schema_version: str = "1.0"
    slug: str
    source: Source
    classification: Classification = Classification()
    ratings: Ratings
    concise: Concise
    detailed: Detailed
    critical: Critical = Critical()
    entities: list[Entity] = []
    related_reports: list[RelatedReport] = []
    confidence: str = "high"
    model_used: str
    status: str = "ok"