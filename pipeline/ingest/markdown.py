import re
from pathlib import Path

import frontmatter

from .. import io_paths
from .normalize import NormalizedDoc, DocMetadata, Section, make_slug

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_WIKILINK = re.compile(r"\[\[(.*?)\]\]")


def _strip_wikilink(s: str) -> str:
    m = _WIKILINK.fullmatch(s.strip())
    return m.group(1) if m else s.strip()


def _split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    cur_h, cur_body = "", []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            if cur_h or cur_body:
                sections.append(Section(cur_h, "\n".join(cur_body).strip()))
            cur_h, cur_body = m.group(2).strip(), []
        else:
            cur_body.append(line)
    if cur_h or cur_body:
        sections.append(Section(cur_h, "\n".join(cur_body).strip()))
    return sections


def parse_markdown_file(path: Path, cfg: dict) -> NormalizedDoc:
    clip_root = io_paths.paths.clippings(cfg)
    rel = str(path.resolve().relative_to(clip_root.resolve())).replace("\\", "/")
    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    fm, body = post.metadata, post.content
    institution = path.parent.name
    authors = [_strip_wikilink(a) for a in (fm.get("author") or [])]
    title = fm.get("title") or path.stem
    published = fm.get("published") or (str(fm.get("created")) if fm.get("created") else None)
    url = fm.get("source")
    return NormalizedDoc(
        slug=make_slug(rel),
        source_path=rel,
        source_type="wechat",
        metadata=DocMetadata(
            institution=institution, title=title, authors=authors,
            published=published, original_url=url,
        ),
        clean_text=body,
        tables=[],
        sections=_split_sections(body),
    )