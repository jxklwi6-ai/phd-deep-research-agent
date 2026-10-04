#!/usr/bin/env python3
"""Offline research ledger, conservative normalization, audit export, and checkpoints.

No network activity, article fetching, or model calls. Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from report_contract import inspect as inspect_report, new_draft, new_review, report_blocks, refs_of

FAMILIES = ("broad", "narrow", "synonym", "method", "application", "platform",
            "citation", "recent", "review", "counterfactual")
ROUTES = ("keyword", "backward", "forward", "related", "recent")
ANCHOR_ROUTES = ("backward", "forward", "related", "review", "exact_method", "competing")
ROLE = ("core", "supporting", "peripheral", "uncertain", "excluded")
SCREEN = ("include", "likely_include", "uncertain", "likely_exclude", "exclude")
ACCESS = ("FULLTEXT", "PARTIAL", "ABSTRACT", "METADATA", "UNAVAILABLE")
EVENT_STATUS = ("COMPLETED", "PARTIAL", "FAILED", "UNAVAILABLE", "NOT_APPLICABLE")
KINDS = {
    "papers": "id", "sources": "source_id", "evidence": "evidence_id",
    "claims": "claim_id", "coverage_matrix": "subquestion",
    "anchors": "subquestion", "anchor_audit": "audit_id",
    "deep_reading_queue": "paper_id", "rounds": "round",
    "failure_diagnostics": "failure_id",
}
WHOLE = ("question_decomposition", "query_families", "checkpoint", "report_draft",
         "narrative_plan", "editorial_review")
CORE_FILES = ("manifest.json", "question_decomposition.json", "query_families.json",
              "retrieval_ledger.jsonl", "papers.json", "sources.json", "evidence.json",
              "claims.json", "coverage_matrix.json", "anchors.json", "anchor_audit.json",
              "deep_reading_queue.json", "rounds.json", "saturation_report.json",
              "failure_diagnostics.json", "checkpoint.json", "report_draft.json",
              "narrative_plan.json", "editorial_review.json")
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def read(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(prefix=".research-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_list(project: Path, stem: str) -> list[dict]:
    value = read(project / (stem + ".json"), [])
    if not isinstance(value, list):
        raise ValueError(stem + ".json must be a JSON list")
    return value


def ledger(project: Path) -> list[dict]:
    path = project / "retrieval_ledger.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def normalize_doi(raw: Any) -> str:
    value = str(raw or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I).rstrip(".,; ")
    if value and not DOI_PATTERN.match(value):
        raise ValueError("Malformed DOI; do not invent or silently repair it: " + value)
    return value.lower()


def norm_title(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold(), flags=re.U)


def first_author(record: dict) -> str:
    authors = record.get("authors") or []
    if isinstance(authors, list):
        return str(authors[0] if authors else "").casefold().strip()
    return str(authors).split(",")[0].casefold().strip()


def unique_join(old: Any, new: Any) -> list:
    out = []
    for entry in list(old or []) + list(new or []):
        if entry not in out:
            out.append(entry)
    return out


def paper_id(record: dict) -> str:
    key = record.get("doi") or (norm_title(record.get("title", "")) + first_author(record)
                                 + str(record.get("year", "")))
    return "P" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:14]


def _paper_validate(record: dict) -> dict:
    paper = dict(record)
    if not str(paper.get("title", "")).strip():
        raise ValueError("Paper record requires a title")
    paper["doi"] = normalize_doi(paper.get("doi"))
    if not paper.get("id") and not paper["doi"] and not (
            first_author(paper) and paper.get("year")):
        raise ValueError("Without DOI, automatic paper identity needs first author and year")
    paper.setdefault("id", paper_id(paper))
    if paper.get("role", "uncertain") not in ROLE:
        raise ValueError("Unrecognized paper role")
    if paper.get("screening_state", "uncertain") not in SCREEN:
        raise ValueError("Unrecognized screening state")
    paper.setdefault("role", "uncertain")
    paper.setdefault("screening_state", "uncertain")
    paper.setdefault("identity_checked", False)
    paper.setdefault("record_type", "paper")
    paper.setdefault("discovery_paths", [])
    paper.setdefault("topics", [])
    paper.setdefault("public_urls", [])
    return paper


def _paper_match(existing: dict, incoming: dict) -> bool:
    if existing["id"] == incoming["id"]:
        if existing.get("doi") and incoming.get("doi") and existing["doi"] != incoming["doi"]:
            raise ValueError("Same ID has conflicting DOI")
        if norm_title(existing["title"]) != norm_title(incoming["title"]) and not (
                existing.get("doi") and existing["doi"] == incoming.get("doi")):
            raise ValueError("Same ID has conflicting titles")
        return True
    if existing.get("doi") and incoming.get("doi"):
        return existing["doi"] == incoming["doi"]
    ids = ("arxiv_id", "pmid", "openalex_id", "semantic_scholar_id")
    for field in ids:
        if existing.get(field) and incoming.get(field) and existing[field] == incoming[field]:
            if existing.get("doi") and incoming.get("doi") and existing["doi"] != incoming["doi"]:
                raise ValueError("Database ID collision with conflicting DOI")
            return True
    return bool(norm_title(existing.get("title", "")) == norm_title(incoming["title"])
                and first_author(existing) and first_author(existing) == first_author(incoming)
                and existing.get("year") and incoming.get("year")
                and abs(int(existing["year"]) - int(incoming["year"])) <= 1
                and not (existing.get("doi") and incoming.get("doi")
                         and existing["doi"] != incoming["doi"]))


def _merge_paper(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    for key, val in incoming.items():
        if key == "id":
            continue
        if key in ("discovery_paths", "topics", "methods", "public_urls", "version_links",
                   "keywords", "references", "related_work_ids"):
            out[key] = unique_join(existing.get(key), val)
        elif val is not None and val != "":
            if key == "role" and existing.get("role") == "core" and val != "core":
                if not incoming.get("role_change_reason"):
                    raise ValueError("Demoting a Core paper requires role_change_reason")
            out[key] = val
    out["id"] = existing["id"]
    return out


def _paper_index_keys(record: dict, adjacent_years: bool = False) -> set[tuple]:
    keys = {("id", str(record["id"]))}
    if record.get("doi"):
        keys.add(("doi", record["doi"]))
    for field in ("arxiv_id", "pmid", "openalex_id", "semantic_scholar_id"):
        if record.get(field):
            keys.add((field, str(record[field])))
    if norm_title(record.get("title", "")) and first_author(record) and record.get("year"):
        year = int(record["year"])
        years = (year - 1, year, year + 1) if adjacent_years else (year,)
        for value in years:
            keys.add(("title-author-year", norm_title(record["title"]), first_author(record), value))
    return keys


def upsert_papers(project: Path, records: list[dict]) -> dict:
    papers = load_list(project, "papers")
    aliases = read(project / "identity_aliases.json", {})
    index = defaultdict(set)
    for position, paper in enumerate(papers):
        for key in _paper_index_keys(paper):
            index[key].add(position)
    actions = []
    for raw in records:
        incoming = _paper_validate(raw)
        candidates = set().union(*(index.get(key, set()) for key in
                                   _paper_index_keys(incoming, adjacent_years=True)))
        hits = [i for i in sorted(candidates) if _paper_match(papers[i], incoming)]
        if len(hits) > 1:
            raise ValueError("Ambiguous normalization: incoming record matches several papers")
        if hits:
            previous = papers[hits[0]]
            explicit = {key: value for key, value in incoming.items()
                        if key in raw or key == "doi"}
            merged = _merge_paper(previous, explicit)
            papers[hits[0]] = merged
            for key in _paper_index_keys(merged):
                index[key].add(hits[0])
            aliases[incoming["id"]] = merged["id"]
            actions.append({"input": incoming["id"], "canonical": merged["id"], "action": "merged"})
        else:
            papers.append(incoming)
            for key in _paper_index_keys(incoming):
                index[key].add(len(papers) - 1)
            aliases[incoming["id"]] = incoming["id"]
            actions.append({"input": incoming["id"], "canonical": incoming["id"], "action": "added"})
    write(project / "papers.json", papers)
    write(project / "identity_aliases.json", aliases)
    return {"papers": len(papers), "actions": actions}


def upsert_generic(project: Path, kind: str, records: list[dict]) -> dict:
    key = KINDS[kind]
    current = load_list(project, kind)
    positions = {str(r[key]): index for index, r in enumerate(current)}
    for item in records:
        if not isinstance(item, dict) or not str(item.get(key, "")).strip():
            raise ValueError(kind + " record requires " + key)
        identifier = str(item[key])
        if identifier in positions:
            old = current[positions[identifier]]
            if kind in ("sources", "evidence", "claims") and old.get("paper_id") != item.get("paper_id"):
                raise ValueError("Cannot move a sourced record between papers")
            current[positions[identifier]] = {**old, **item}
        else:
            positions[identifier] = len(current)
            current.append(item)
    write(project / (kind + ".json"), current)
    return {"kind": kind, "count": len(current)}


def init(project: Path, question: str, as_of: str, language: str) -> dict:
    if not question.strip():
        raise ValueError("Question must not be blank")
    datetime.fromisoformat(as_of)
    project.mkdir(parents=True, exist_ok=True)
    if (project / "manifest.json").exists():
        present = read(project / "manifest.json")
        if present["question"] != question:
            raise ValueError("Existing project belongs to another question; resume or choose a new project")
        if present["as_of_date"] != as_of:
            raise ValueError("Existing project has a different search cutoff (" + present["as_of_date"] +
                             "); use a new project for the requested cutoff or explicitly resume the stored cutoff. Prior records are unchanged.")
        if not (project / "narrative_plan.json").exists():
            write(project / "narrative_plan.json", {"main_storyline": "", "core_tension": "",
                  "chapter_questions": [], "overall_insights": []})
        if not (project / "editorial_review.json").exists():
            write(project / "editorial_review.json", new_review())
        return {"resumed": True, "project": str(project), "rewrite_report_for_v31":
                read(project / "report_draft.json", {}).get("format_version") != "3.1"}
    manifest = {"schema_version": 3, "question": question, "as_of_date": as_of,
                "skill_version": "3.1.0", "report_format_version": "3.1",
                "report_language": language, "execution_mode": "HOST_WEB_SEARCH_BROWSE"}
    write(project / "manifest.json", manifest)
    write(project / "question_decomposition.json",
          {"question": question, "subquestions": [{"id": "main", "text": question}],
           "assumptions": [], "alternative_interpretations": [], "exclusions": [],
           "date_focus": "", "scientific_dimensions": []})
    write(project / "query_families.json",
          {"families": [{"name": name, "status": "PLANNED", "reason": ""} for name in FAMILIES]})
    for stem in KINDS:
        write(project / (stem + ".json"), [])
    write(project / "saturation_report.json", {"saturated": False, "status": "IN_PROGRESS"})
    write(project / "checkpoint.json", {"question": question, "phase": "DISCOVERY",
          "round": 1, "completed_routes": [], "coverage_gaps": [],
          "anchor_state": [], "source_failures": [], "next_action": "formulate queries",
          "status": "IN_PROGRESS"})
    write(project / "report_draft.json", new_draft(as_of))
    write(project / "narrative_plan.json", {"main_storyline": "", "core_tension": "",
          "chapter_questions": [], "overall_insights": []})
    write(project / "editorial_review.json", new_review())
    write(project / "identity_aliases.json", {})
    (project / "retrieval_ledger.jsonl").touch()
    return {"created": True, "project": str(project)}


def append_event(project: Path, event: dict) -> dict:
    required = ("query_id", "round", "family", "route", "source", "query", "status",
                "observed_returned_count", "candidate_ids")
    absent = [key for key in required if key not in event]
    if absent:
        raise ValueError("Event lacks: " + ", ".join(absent))
    if event["status"] not in EVENT_STATUS:
        raise ValueError("Unknown query status")
    if not isinstance(event["candidate_ids"], list):
        raise ValueError("candidate_ids must be an array")
    if int(event["observed_returned_count"]) < len(event["candidate_ids"]):
        raise ValueError("Observed returned count cannot be smaller than candidate ID count")
    item = dict(event)
    item.setdefault("event_id", uuid.uuid4().hex)
    item.setdefault("timestamp", datetime.now().astimezone().isoformat(timespec="seconds"))
    old = {r.get("event_id"): r for r in ledger(project)}
    if item["event_id"] in old:
        if item != old[item["event_id"]]:
            raise ValueError("event_id already exists with different data")
        return {"already_recorded": item["event_id"]}
    with (project / "retrieval_ledger.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return {"recorded": item["event_id"]}


def canonical(project: Path, identifier: str) -> str:
    return str(read(project / "identity_aliases.json", {}).get(identifier, identifier))


def counts(project: Path) -> dict:
    papers = load_list(project, "papers")
    events = ledger(project)
    sources = load_list(project, "sources")
    refs = {p["id"] for p in papers}
    read_levels = defaultdict(list)
    read_surfaces = Counter()
    for source in sources:
        if source.get("read_state") == "READ":
            read_levels[canonical(project, source["paper_id"])].append(source.get("access_level"))
            read_surfaces[source.get("retrieval_surface", "HOST_OPEN_PAGE")] += 1
    priority = ["FULLTEXT", "PARTIAL", "ABSTRACT", "METADATA"]
    highest = {}
    for paper_id, levels in read_levels.items():
        highest[paper_id] = next((level for level in priority if level in levels), "UNAVAILABLE")
    observed = set()
    for ev in events:
        observed.update(canonical(project, p) for p in ev.get("candidate_ids", []))
    return {
        "query_events": len(events),
        "completed_query_events": sum(ev.get("status") == "COMPLETED" for ev in events),
        "failed_or_unavailable_query_events": sum(ev.get("status") in ("FAILED", "UNAVAILABLE")
                                                 for ev in events),
        "observed_result_entries": sum(int(ev.get("observed_returned_count", 0)) for ev in events),
        "distinct_candidate_ids_in_ledger": len(observed),
        "distinct_paper_records": len([p for p in papers if p.get("record_type") != "web"]),
        "distinct_work_groups": len({p.get("version_group") or p["id"] for p in papers
                                    if p.get("record_type") != "web"}),
        "paper_roles": dict(Counter(p["role"] for p in papers)),
        "screening_states": dict(Counter(p["screening_state"] for p in papers)),
        "highest_actually_read_level_by_paper": dict(Counter(highest.values())),
        "read_source_records_by_surface": dict(read_surfaces),
        "papers_without_read_source": len(refs - set(highest)),
        "failed_query_events": len([e for e in events if e.get("status") in ("FAILED", "UNAVAILABLE")]),
        "diagnostic_failure_records": len(load_list(project, "failure_diagnostics")),
        "denominator_note": "Counts describe observed web-tool results and stored paper identities; "
                            "they do not estimate the size of the total literature."
    }


def _routes_by_round(project: Path, events: list[dict], round_no: int) -> set[tuple]:
    return {(re.sub(r"\s+", " ", str(e.get("query", "")).casefold()).strip(),
             e.get("route"), e.get("source"))
            for e in events if int(e.get("round", 0)) == round_no
            and e.get("status") == "COMPLETED"}


def evaluate(project: Path) -> dict:
    events = ledger(project)
    papers = load_list(project, "papers")
    rounds = sorted(load_list(project, "rounds"), key=lambda r: int(r["round"]))
    families = read(project / "query_families.json", {"families": []}).get("families", [])
    covered = {e.get("family") for e in events if e.get("status") == "COMPLETED"}
    routes = {e.get("route") for e in events if e.get("status") == "COMPLETED"}
    configured = {f["name"]: f for f in families}
    missing_families = [name for name in FAMILIES if name not in covered
                        and not (configured.get(name, {}).get("status") == "NOT_APPLICABLE"
                                 and configured[name].get("reason"))]
    missing_routes = sorted(set(ROUTES) - routes)
    anchors = load_list(project, "anchor_audit")
    questions = read(project / "question_decomposition.json", {}).get("subquestions", [])
    missing_anchor = [(q["id"], route) for q in questions for route in ANCHOR_ROUTES
                      if not any(a.get("subquestion") == q["id"] and a.get("route") == route
                                 and (a.get("status") == "COMPLETED" or
                                      a.get("status") == "NOT_APPLICABLE" and a.get("reason"))
                                 for a in anchors)]
    gaps = [row.get("subquestion") for row in load_list(project, "coverage_matrix")
            if row.get("gap_severity") == "important"]
    fingerprints_prior = set()
    trajectories = []
    for row in rounds:
        number = int(row["round"])
        here = [e for e in events if int(e.get("round", 0)) == number
                and e.get("status") == "COMPLETED"]
        fingerprints = _routes_by_round(project, events, number)
        fresh = fingerprints - fingerprints_prior
        fingerprints_prior |= fingerprints
        candidates = {canonical(project, p) for e in here for p in e.get("candidate_ids", [])}
        relevant_new = [p["id"] for p in papers if p["id"] in candidates
                        and int(p.get("first_seen_round") or number) == number
                        and p.get("screening_state") in ("include", "likely_include")]
        new_core = [p["id"] for p in papers if p.get("role") == "core"
                    and int(p.get("role_assigned_round") or p.get("first_seen_round") or number) == number]
        rate = len(relevant_new) / len(candidates) if candidates else None
        trajectories.append({"round": number, "actual_unique_candidate_denominator": len(candidates),
            "new_relevant_ids": relevant_new, "new_core_ids": new_core, "new_concepts": row.get("new_concepts", []),
            "new_contradictions": row.get("new_contradictions", []), "new_terms": row.get("new_terms", []),
            "novelty_rate": rate, "fresh_query_route_source_combinations": len(fresh),
            "eligible_low_novelty": bool(fresh and candidates and rate is not None and rate < 0.05
                and not new_core and not row.get("new_concepts") and not row.get("new_contradictions")
                and not row.get("new_terms"))})
    two = len(trajectories) >= 2 and all(r["eligible_low_novelty"] for r in trajectories[-2:])
    saturated = not (missing_families or missing_routes or missing_anchor or gaps) and two
    state = {"saturated": saturated, "status": "SATURATED" if saturated else "NOT_SATURATED",
             "threshold": 0.05, "required_low_novelty_rounds": 2,
             "missing_query_families": missing_families,
             "missing_routes": missing_routes,
             "missing_anchor_audits": [{"subquestion": q, "route": route} for q, route in missing_anchor],
             "important_gaps": gaps, "round_trajectory": trajectories,
             "interpretation": "Saturation does not imply exhaustive coverage."}
    write(project / "saturation_report.json", state)
    return state


def validate(project: Path, final: bool = False) -> list[str]:
    errors = []
    manifest = read(project / "manifest.json")
    if not manifest:
        return ["Missing manifest.json; initialize a project first"]
    papers = load_list(project, "papers")
    sources = load_list(project, "sources")
    evidence = load_list(project, "evidence")
    claims = load_list(project, "claims")
    ids = {p["id"]: p for p in papers}
    source_ids = {s["source_id"]: s for s in sources}
    evidence_ids = {e["evidence_id"]: e for e in evidence}
    claim_ids = {c["claim_id"]: c for c in claims}
    for paper in papers:
        if not paper.get("title") or paper.get("role") not in ROLE or paper.get("screening_state") not in SCREEN:
            errors.append("Invalid paper record: " + str(paper.get("id")))
        if final and not paper.get("identity_checked") and paper.get("role") not in ("excluded", "peripheral"):
            errors.append("Unverified included paper identity: " + paper["id"])
        if final and paper.get("role") not in ("excluded", "peripheral") and not paper.get("first_seen_round"):
            errors.append("Included paper missing first_seen_round: " + paper["id"])
        if final and paper.get("role") == "core" and not paper.get("role_assigned_round"):
            errors.append("Core paper missing role_assigned_round: " + paper["id"])
    for src in sources:
        sid = src["source_id"]
        if canonical(project, src.get("paper_id", "")) not in ids:
            errors.append("Source missing paper: " + sid)
        if src.get("access_level") not in ACCESS or src.get("read_state") not in ("READ", "NOT_READ", "FAILED"):
            errors.append("Source has invalid access/read state: " + sid)
        surface = src.get("retrieval_surface", "HOST_OPEN_PAGE")
        if surface not in ("HOST_OPEN_PAGE", "HOST_SEARCH_RESULT"):
            errors.append("Source has invalid retrieval surface: " + sid)
        if surface == "HOST_SEARCH_RESULT" and src.get("read_state") == "READ":
            if src.get("access_level") in ("FULLTEXT", "UNAVAILABLE"):
                errors.append("Indexed search result cannot establish public full text: " + sid)
            if not src.get("tool_result_ref"):
                errors.append("Read indexed result lacks tool-result provenance: " + sid)
            if src.get("access_level") == "ABSTRACT" and not src.get("abstract_complete"):
                errors.append("Indexed abstract is not demonstrably complete: " + sid)
        if not str(src.get("url", "")).startswith(("https://", "http://")):
            errors.append("Source has no public web URL: " + sid)
        if final and src.get("read_state") == "READ" and not src.get("accessed_date"):
            errors.append("Read source missing actual access date: " + sid)
    for item in evidence:
        eid = item["evidence_id"]
        src = source_ids.get(item.get("source_id"))
        if not src or canonical(project, item.get("paper_id", "")) != canonical(
                project, src.get("paper_id", "")):
            errors.append("Evidence source/paper identity mismatch: " + eid)
            continue
        if src.get("read_state") != "READ" or item.get("evidence_level") != src.get("access_level"):
            errors.append("Evidence overstates or mislabels material actually read: " + eid)
        if not item.get("paraphrase") or not item.get("locator"):
            errors.append("Evidence lacks paraphrase/locator: " + eid)
        if item.get("direction") not in ("support", "contradict", "context"):
            errors.append("Evidence lacks direction: " + eid)
    for claim in claims:
        cid = claim["claim_id"]
        evidence_for = [evidence_ids.get(identifier) for identifier in claim.get("evidence_ids", [])]
        if not evidence_for or not all(evidence_for):
            errors.append("Claim lacks valid evidence: " + cid)
            continue
        if claim.get("claim_type") in ("detailed", "figure_table") and not any(
                e.get("evidence_level") == "FULLTEXT" for e in evidence_for):
            errors.append("Detailed/figure claim lacks read public full text: " + cid)
        if claim.get("claim_type") not in ("summary", "detailed", "figure_table", "metadata", "hypothesis"):
            errors.append("Invalid claim type: " + cid)
        if claim.get("claim_type") == "hypothesis" and not claim.get("is_inference"):
            errors.append("Hypothesis not labeled inference: " + cid)
        standing = claim.get("standing")
        if standing not in ("supported", "contradicted", "mixed", "uncertain"):
            errors.append("Claim missing a valid standing: " + cid)
        directions = {e.get("direction") for e in evidence_for}
        if standing == "supported" and "support" not in directions:
            errors.append("Supported claim has no supporting evidence: " + cid)
        if standing == "contradicted" and "contradict" not in directions:
            errors.append("Contradicted claim has no contradictory evidence: " + cid)
        if standing == "mixed" and not {"support", "contradict"}.issubset(directions):
            errors.append("Mixed claim lacks both supporting and contradictory evidence: " + cid)
        if claim.get("claim_type") != "metadata" and not any(
                e.get("evidence_level") in ("FULLTEXT", "PARTIAL", "ABSTRACT") for e in evidence_for):
            errors.append("Scientific claim relies only on metadata: " + cid)
        if claim.get("claim_type") in ("summary", "detailed", "figure_table") and all(
                source_ids[e["source_id"]].get("source_kind") == "secondary"
                for e in evidence_for if e.get("source_id") in source_ids):
            errors.append("Scientific claim has only secondary webpage evidence: " + cid)
    for ev in ledger(project):
        if ev.get("status") == "COMPLETED":
            for ref in ev.get("candidate_ids", []):
                if canonical(project, ref) not in ids:
                    errors.append("Ledger candidate not normalized in papers: " + str(ref))
    if final:
        draft = read(project / "report_draft.json", {})
        result = inspect_report(draft, set(claim_ids), read(project / "narrative_plan.json", {}),
                                read(project / "editorial_review.json", {}))
        errors.extend(result["errors"])
        sat = evaluate(project)
        if not sat["saturated"] and not draft.get("limitations"):
            errors.append("Incomplete coverage requires explicit limitations in the report")
    return sorted(set(errors))


def report_quality(project: Path) -> dict:
    return inspect_report(read(project / "report_draft.json", {}),
                          {c["claim_id"] for c in load_list(project, "claims")},
                          read(project / "narrative_plan.json", {}),
                          read(project / "editorial_review.json", {}))


def audit_summary(project: Path) -> str:
    stats, sat = counts(project), evaluate(project)
    lines = ["文献检索与证据审计 V3.1", "研究问题：" + read(project / "manifest.json")["question"],
             "实际执行方式：" + read(project / "manifest.json")["execution_mode"],
             "本文件是配套审计记录；综述正文保持 TL;DR、引言、主体章、结论与参考文献的连续结构。"]
    labels = {"query_events": "实际检索事件", "completed_query_events": "成功事件",
              "failed_or_unavailable_query_events": "失败或不可用事件",
              "observed_result_entries": "工具返回条目总数", "distinct_candidate_ids_in_ledger": "日志中唯一候选身份",
              "distinct_paper_records": "去重论文记录", "distinct_work_groups": "链接版本后的作品组",
              "papers_without_read_source": "尚无已读来源的论文", "diagnostic_failure_records": "失败诊断记录"}
    lines.extend(label + "：" + str(stats[key]) for key, label in labels.items())
    for key, label in (("paper_roles", "文献地图角色"), ("screening_states", "标题摘要筛选"),
                       ("highest_actually_read_level_by_paper", "每篇最高实际阅读层级"),
                       ("read_source_records_by_surface", "已读来源记录的取得表面")):
        lines.append(label + "：" + json.dumps(stats[key], ensure_ascii=False, sort_keys=True))
    for dimension in ("route", "family"):
        c = Counter((str(e.get(dimension)), str(e.get("status"))) for e in ledger(project))
        lines.append(dimension + " / 状态 / 事件数：")
        lines.extend(f"  {name} / {status} / {number}" for (name, status), number in sorted(c.items()))
    lines.append("饱和判定：" + sat["status"] + "；阈值：" + str(sat["threshold"]))
    for key in ("missing_query_families", "missing_routes", "missing_anchor_audits", "important_gaps", "round_trajectory"):
        lines.append(key + "：" + json.dumps(sat[key], ensure_ascii=False, sort_keys=True))
    for stem in ("question_decomposition", "coverage_matrix", "anchor_audit", "failure_diagnostics"):
        lines.append(stem + "：" + json.dumps(read(project / (stem + ".json")), ensure_ascii=False, sort_keys=True))
    lines.append("写作质量记录：" + json.dumps(report_quality(project), ensure_ascii=False, sort_keys=True))
    lines.append("以上数量只描述实际执行和记录的过程，不能估计全领域召回率；索引摘要不等于全文。")
    return "\n".join(lines) + "\n"


def export(project: Path) -> dict:
    errors = validate(project, final=True)
    if errors:
        raise ValueError("Final audit failed:\n- " + "\n- ".join(errors))
    if (project / "report_citations.json").exists():
        from render_report import CitationIndex
        citation_index = CitationIndex(project)
        for block in report_blocks(read(project / "report_draft.json")):
            if block.get("type") == "table":
                for row in block.get("rows", []):
                    citation_index.numbers(refs_of(row))
            else:
                citation_index.numbers(refs_of(block))
        if read(project / "report_citations.json").get("entries") != citation_index.entries():
            raise ValueError("Citation provenance/metadata changed after rendering; rerender and check the DOCX before export")
        if (project / "report.docx").exists():
            from quality_gate import check
            result = check(project, project / "report.docx")
            if not result["passed"]:
                raise ValueError("DOCX integrity failed before audit export:\n- " + "\n- ".join(result["problems"]))
    papers = load_list(project, "papers")
    events = ledger(project)
    paths = defaultdict(set)
    for ev in events:
        for cid in ev.get("candidate_ids", []):
            paths[canonical(project, cid)].add(str(ev.get("query_id")))
    fields = ("id", "title", "authors", "year", "venue", "doi", "record_type",
              "version_group", "topics", "methods", "system", "platform", "key_contribution",
              "limitations", "relevance_reason", "role", "screening_state",
              "anchor_score", "access_status", "reading_priority", "public_urls",
              "discovery_query_ids", "discovery_path_count", "highest_read_level", "read_source_surfaces")
    sources = load_list(project, "sources")
    csvpath = project / "literature_map.csv"
    with csvpath.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for paper in papers:
            if paper.get("record_type") == "web":
                continue
            row = {name: paper.get(name, "") for name in fields}
            row["discovery_query_ids"] = "; ".join(sorted(paths.get(paper["id"], set())))
            row["discovery_path_count"] = len(paths.get(paper["id"], set()))
            seen = [s for s in sources if canonical(project, s.get("paper_id", "")) == paper["id"]
                    and s.get("read_state") == "READ"]
            row["highest_read_level"] = next((level for level in ("FULLTEXT", "PARTIAL", "ABSTRACT", "METADATA")
                                             if any(s.get("access_level") == level for s in seen)), "UNAVAILABLE")
            row["read_source_surfaces"] = sorted({s.get("retrieval_surface", "HOST_OPEN_PAGE") for s in seen})
            for key, value in row.items():
                if isinstance(value, (list, dict)):
                    row[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            writer.writerow(row)
    write(project / "audit_stats.json", counts(project))
    write(project / "report_quality.json", report_quality(project))
    (project / "research_audit.txt").write_text(audit_summary(project), encoding="utf-8")
    zippath = project / "research_audit.zip"
    with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as zf:
        names = CORE_FILES + ("identity_aliases.json", "audit_stats.json", "report_quality.json",
                              "research_audit.txt", "literature_map.csv")
        if (project / "report_citations.json").exists():
            names += ("report_citations.json",)
        for name in sorted(names):
            zf.write(project / name, arcname=name)
    return {"literature_map": str(csvpath), "research_audit": str(zippath),
            "papers": len(papers), "events": len(events)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("init")
    start.add_argument("--project", type=Path, required=True)
    start.add_argument("--question", required=True)
    start.add_argument("--as-of", default=datetime.now().astimezone().date().isoformat())
    start.add_argument("--language", default="zh-CN")
    for command in ("event", "upsert", "put"):
        part = sub.add_parser(command)
        part.add_argument("--project", type=Path, required=True)
        part.add_argument("--input", type=Path, required=True)
        if command in ("upsert", "put"):
            part.add_argument("--kind", choices=sorted(KINDS if command == "upsert" else WHOLE),
                              required=True)
    for command in ("stats", "evaluate", "validate", "export"):
        part = sub.add_parser(command)
        part.add_argument("--project", type=Path, required=True)
        if command == "validate":
            part.add_argument("--final", action="store_true")
    args = parser.parse_args()
    try:
        project = args.project.resolve()
        if args.command == "init":
            result = init(project, args.question, args.as_of, args.language)
        else:
            if not (project / "manifest.json").exists():
                raise ValueError("Project has not been initialized")
            if args.command == "event":
                result = append_event(project, read(args.input))
            elif args.command == "upsert":
                incoming = read(args.input)
                if not isinstance(incoming, list):
                    raise ValueError("Upsert input must be a JSON array")
                result = (upsert_papers(project, incoming) if args.kind == "papers"
                          else upsert_generic(project, args.kind, incoming))
            elif args.command == "put":
                item = read(args.input)
                if not isinstance(item, dict):
                    raise ValueError("Whole artifact must be a JSON object")
                if args.kind == "checkpoint":
                    old = read(project / "checkpoint.json", {})
                    item = {**old, **item}
                write(project / (args.kind + ".json"), item)
                result = {"written": args.kind}
            elif args.command == "stats":
                result = counts(project)
            elif args.command == "evaluate":
                result = evaluate(project)
            elif args.command == "validate":
                problems = validate(project, final=args.final)
                result = {"valid": not problems, "problems": problems}
                if problems:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    sys.exit(1)
            else:
                result = export(project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
