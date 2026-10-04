#!/usr/bin/env python3
"""Offline V3.1 report structure checks; semantic review remains the author's job."""
from __future__ import annotations

import re
from typing import Iterator

FORMAT_VERSION = "3.1"
TLDR_ROLES = ("object", "state", "advances", "limits", "reader_takeaway")
TLDR_LABELS = ("研究对象", "当前总体认识", "近年重要进展", "目前主要限制", "阅读导览")
INTRO_ROLES = {"object_value", "principles_history", "development_status", "bottleneck", "scope_roadmap"}
CONCLUSION_ROLES = {"field_state", "scientific_synthesis", "key_unresolved", "grounded_outlook"}
REVIEW_KEYS = ("tldr", "introduction", "overall_structure", "body_overview", "chapter_opening",
               "subsections", "literature_synthesis", "comparison", "chapter_closing", "quantitative_data",
               "evidence_strength", "conflicting_evidence", "tables", "heading_density", "conclusion",
               "grounded_outlook", "citations", "bibliographic_identity", "continuous_readability")
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
RAW_CITATION = re.compile(r"\[\d+(?:\s*[,\-–]\s*\d+)*\]")


def text_of(block: dict) -> str:
    if block.get("spans"):
        return "".join(str(s.get("text", "")) for s in block["spans"])
    if block.get("type") == "table":
        return " ".join(str(c) for row in block.get("rows", []) for c in row.get("cells", []))
    return str(block.get("text", ""))


def refs_of(block: dict) -> list[str]:
    values = list(block.get("claim_ids", []))
    for span in block.get("spans", []):
        values.extend(span.get("claim_ids", []))
    return list(dict.fromkeys(values))


def report_blocks(draft: dict) -> Iterator[dict]:
    yield from draft.get("tldr", [])
    for section in draft.get("sections", []):
        if section.get("kind") in ("introduction", "conclusion"):
            yield from section.get("blocks", [])
        else:
            if isinstance(section.get("opening"), dict):
                yield section["opening"]
            for sub in section.get("subsections", []):
                yield from sub.get("blocks", [])
            if isinstance(section.get("closing"), dict):
                yield section["closing"]


def new_draft(as_of: str) -> dict:
    return {"format_version": FORMAT_VERSION, "title": "", "as_of_date": as_of,
            "length_profile": "full", "length_reason": "", "tldr": [], "sections": [],
            "limitations": [], "execution_mode": "HOST_WEB_SEARCH_BROWSE"}


def new_review() -> dict:
    return {"format_version": FORMAT_VERSION, "items": {
        key: {"status": "PENDING", "basis": "", "locations": []} for key in REVIEW_KEYS}}


def inspect(draft: dict, known_claims: set[str], plan: dict, review: dict) -> dict:
    errors, warnings = [], []
    if draft.get("format_version") != FORMAT_VERSION:
        errors.append("Report draft must use format_version 3.1; rewrite a V3 draft into the new narrative schema")
    if not str(draft.get("title", "")).strip():
        errors.append("Missing specific report title")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(draft.get("as_of_date", ""))):
        errors.append("Report needs a YYYY-MM-DD search cutoff")
    sections = draft.get("sections", [])
    kinds = [s.get("kind") for s in sections]
    if not kinds or kinds[0] != "introduction" or kinds[-1] != "conclusion":
        errors.append("Required order: introduction, 3-6 body chapters, conclusion")
    if kinds.count("introduction") != 1 or kinds.count("conclusion") != 1:
        errors.append("Exactly one introduction and one conclusion are mandatory")
    if any(k not in {"introduction", "overview", "theme", "limitations", "conclusion"} for k in kinds):
        errors.append("No standalone audit, scope, gap, or evidence-matrix chapters are allowed")
    body = sections[1:-1] if kinds else []
    if not 3 <= len(body) <= 6:
        errors.append("Body must contain 3-6 major chapters including overview and limitations")
    if not body or body[0].get("kind") != "overview" or body[-1].get("kind") != "limitations":
        errors.append("Body must begin with overall field development and end with limitations/controversies/frontiers")
    if body and (sum(s.get("kind") == "overview" for s in body) != 1 or
                 sum(s.get("kind") == "limitations" for s in body) != 1):
        errors.append("Use one overall field chapter and one final limitations chapter")
    tldr = draft.get("tldr", [])
    if [p.get("role") for p in tldr] != list(TLDR_ROLES):
        errors.append("TL;DR requires five ordered parts: object, state, advances, limits, reader_takeaway")

    def check_block(block: dict, where: str, allow_table: bool = True) -> None:
        typ = block.get("type", "paragraph")
        if typ == "table":
            if not allow_table:
                errors.append(where + " must be continuous prose, not a table")
            columns, rows = block.get("columns", []), block.get("rows", [])
            if not columns or not rows:
                errors.append(where + " contains an empty comparison table")
            for i, row in enumerate(rows):
                if len(row.get("cells", [])) != len(columns):
                    errors.append(where + " table row does not match columns")
                check_refs(row, where + " row " + str(i + 1))
            return
        if typ != "paragraph":
            errors.append(where + " has an unsupported block/heading type")
            return
        text = text_of(block)
        if not text.strip():
            errors.append(where + " has no substantive paragraph")
        if block.get("spans") and (block.get("text") or block.get("claim_ids")):
            errors.append(where + " must use spans or whole-paragraph text/claim_ids, not both")
        if RAW_CITATION.search(text):
            errors.append(where + " contains pre-numbered references; use claim_ids for deterministic numbering")
        if "```" in text or re.search(r"(?m)^#{1,4}\s", text):
            errors.append(where + " contains raw Markdown formatting")
        if block.get("spans"):
            for i, span in enumerate(block["spans"]):
                merged = {"content_kind": block.get("content_kind", "scientific"), **span}
                check_refs(merged, where + " span " + str(i + 1))
        else:
            check_refs(block, where)

    def check_refs(block: dict, where: str) -> None:
        refs = refs_of(block)
        if block.get("content_kind", "scientific") not in ("scientific", "method", "scope"):
            errors.append(where + " has an invalid content kind")
        if block.get("content_kind", "scientific") == "scientific" and not refs:
            errors.append(where + " has scientific content without claim IDs")
        for cid in refs:
            if cid not in known_claims:
                errors.append(where + " has an unknown claim ID: " + str(cid))

    for i, block in enumerate(tldr):
        check_block(block, "TL;DR part " + str(i + 1), False)
    for i, section in enumerate(sections):
        where = "Section " + str(i + 1)
        if not str(section.get("title", "")).strip():
            errors.append(where + " is missing a problem-centered title")
        if section.get("kind") in ("introduction", "conclusion"):
            required_title = "引言" if section["kind"] == "introduction" else "结论与展望"
            if section.get("title") != required_title:
                errors.append(where + " must be titled " + required_title)
            blocks = section.get("blocks", [])
            target = (4, 6) if section["kind"] == "introduction" else (3, 5)
            if not target[0] <= len(blocks) <= target[1]:
                warnings.append(where + " paragraph count is outside the recommended " + str(target))
            roles = {r for p in blocks for r in p.get("roles", [])}
            required = INTRO_ROLES if section["kind"] == "introduction" else CONCLUSION_ROLES
            if not required.issubset(roles):
                errors.append(where + " is missing narrative functions: " + ", ".join(sorted(required - roles)))
            for j, block in enumerate(blocks):
                check_block(block, where + " paragraph " + str(j + 1), False)
        else:
            for position in ("opening", "closing"):
                block = section.get(position)
                if not isinstance(block, dict):
                    errors.append(where + " is missing its " + position + " synthesis paragraph")
                else:
                    check_block(block, where + " " + position, False)
            subs = section.get("subsections", [])
            if not 2 <= len(subs) <= 4:
                errors.append(where + " requires 2-4 substantive subthemes")
            for j, sub in enumerate(subs):
                if not sub.get("title") or not sub.get("blocks"):
                    errors.append(where + " subsection is empty")
                if sub.get("blocks") and sub["blocks"][0].get("type", "paragraph") != "paragraph":
                    errors.append(where + " subsection must open with a synthesis judgment in prose")
                for k, block in enumerate(sub.get("blocks", [])):
                    check_block(block, where + f" subsection {j + 1} block {k + 1}")

    blocks = list(report_blocks(draft))
    all_text = "\n".join(text_of(b) for b in blocks)
    for limitation in draft.get("limitations", []):
        if limitation and limitation not in all_text:
            errors.append("A material limitation exists only in metadata; integrate its exact text into the scope/limitations prose")
    if not plan.get("main_storyline") or not plan.get("core_tension"):
        errors.append("Internal narrative plan needs one main storyline and a core scientific tension")
    if not 3 <= len(plan.get("overall_insights", [])) <= 5:
        errors.append("Internal narrative plan needs 3-5 overall insights")
    if len(plan.get("chapter_questions", [])) != len(body):
        errors.append("Internal narrative plan must map one scientific question to each body chapter")
    for key in REVIEW_KEYS:
        item = review.get("items", {}).get(key, {})
        if item.get("status") not in ("PASS", "LIMITED") or not item.get("basis"):
            errors.append("Editorial self-review is incomplete or failed: " + key)
        if item.get("status") == "LIMITED" and not draft.get("limitations"):
            errors.append("Limited editorial result needs a visible research limitation: " + key)
    tldr_count = len(CJK.findall("".join(text_of(p) for p in tldr)))
    total_count = len(CJK.findall(all_text))
    table_count = sum(b.get("type") == "table" for b in blocks)
    subsection_count = sum(len(s.get("subsections", [])) for s in body)
    if not 400 <= tldr_count <= 800:
        warnings.append("TL;DR is outside the approximately 400-800 Chinese-character target")
    profile = draft.get("length_profile", "full")
    if profile not in ("full", "user_concise", "user_custom", "evidence_limited"):
        errors.append("Unknown length profile")
    if profile != "full" and not draft.get("length_reason"):
        errors.append("A concise/evidence-limited report needs a recorded reason")
    if profile == "full" and not 6000 <= total_count <= 12000:
        errors.append("Default full report must meet the 6000-12000 Chinese-character target; revise substantively or record a justified user/evidence-limited profile, never pad")
    if profile == "full" and not 400 <= tldr_count <= 800:
        errors.append("Default full report needs a 400-800 Chinese-character TL;DR")
    if profile == "evidence_limited" and not draft.get("limitations"):
        errors.append("Evidence-limited length requires an actual visible evidence/access limitation")
    if not 2 <= table_count <= 4:
        warnings.append("Report is outside the typical 2-4 useful comparison tables; use only tables that aid comparison")
    proportions = {}
    for kind, target in (("introduction", (.08, .12)), ("conclusion", (.06, .10))):
        size = sum(len(CJK.findall(text_of(b))) for s in sections if s.get("kind") == kind
                   for b in s.get("blocks", []))
        ratio = size / total_count if total_count else 0
        proportions[kind] = round(ratio, 4)
        if total_count and not target[0] <= ratio <= target[1]:
            warnings.append(kind + " proportion differs from the recommended range")
    return {"passed": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)),
            "metrics": {"chinese_characters": total_count, "tldr_chinese_characters": tldr_count,
                        "body_chapters": len(body), "numbered_chapters": len(sections),
                        "subsections": subsection_count, "comparison_tables": table_count,
                        "section_proportions": proportions},
            "semantic_review_note": "Structural checks cannot prove that prose synthesizes the literature; reread every chapter and its sources."}
