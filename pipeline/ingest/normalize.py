from dataclasses import dataclass, field
import hashlib


@dataclass
class Section:
    heading: str
    body: str


@dataclass
class DocMetadata:
    institution: str
    title: str
    authors: list[str] = field(default_factory=list)
    published: str | None = None
    original_url: str | None = None


@dataclass
class NormalizedDoc:
    slug: str
    source_path: str
    source_type: str  # wechat | pdf | official | article
    metadata: DocMetadata
    clean_text: str
    tables: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)


def make_slug(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]