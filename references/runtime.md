# V3.1 host runtime and helper commands

The package supplies a workflow and original offline code; it cannot activate tools or a separate Deep Research mode. Use the host's actual web search/open tools for every online lookup. The scripts perform no network or model calls. Word creation uses python-docx; requirements.txt declares it. Use a host document renderer or LibreOffice/Poppler to inspect all pages.

Keep project outputs outside the installed skill folder. Use the host's Python runtime and resolve the skill path from its resource location; no user-specific path is hardcoded.

1. Run python scripts/run_store.py init --project PROJECT_DIR --question "..." --as-of YYYY-MM-DD. Resume a checkpoint instead of replaying searches. Existing V3 paper/evidence stores are preserved, but the old prose draft must be rewritten in V3.1 form. A resume uses the stored search cutoff; a new date window requires a new project, optionally seeded with the prior corpus. The helper never silently ignores a changed cutoff, and this routine choice does not require user confirmation.
2. For each search/open attempt, record python scripts/run_store.py event --project PROJECT_DIR --input ONE_EVENT.json, including failures and empty returns. Store canonical paper batches with upsert --kind papers; repeat for sources, evidence, claims, coverage_matrix, anchors, anchor_audit, deep_reading_queue, rounds and failure_diagnostics.
3. Use put --kind question_decomposition, query_families or checkpoint for whole JSON objects. Keep interpretations, assumptions and dates traceable.
4. Run evaluate --project PROJECT_DIR; continue searches for real gaps. A budget/tool cap leaves the run unsaturated but still produces a limitations-aware report.
5. Read the complete V3.1 prose specification and assets/report-draft-template.json. Write narrative_plan.json through put --kind narrative_plan. Write actual Chinese review prose to report_draft.json through put --kind report_draft.
6. Reread prose against sources and the 19-item checklist; save editorial_review.json through put --kind editorial_review. Each item requires PASS or LIMITED with a specific basis; correct FAIL/PENDING.
7. Run python scripts/run_store.py validate --project PROJECT_DIR --final. Fix evidence, structure, citation and visible-limitations failures. Meet the default full-report/TL;DR lengths or record an explicit user length request or actual evidence limit. Review proportion/table warnings as editorial targets; never pad merely to hit a count.
8. Run python scripts/render_report.py --project PROJECT_DIR --output PROJECT_DIR/report.docx.
9. Run python scripts/quality_gate.py --project PROJECT_DIR --docx PROJECT_DIR/report.docx. It checks narrative order, citation numbering/placement, ACS typography, work identity and the absence of graphics.
10. Render the DOCX to page images through the host's document tools; inspect every page and revise/rerender when necessary.
11. Run python scripts/run_store.py export --project PROJECT_DIR. Deliver report.docx, literature_map.csv and research_audit.zip. The audit ZIP contains the former audit data plus research_audit.txt, report_quality.json, editorial_review.json, narrative_plan.json and report_citations.json when rendered.

A code gate is a convenience, not proof of scientific completeness or good review writing. The author must verify sources, compare conditions, preserve contradictions and reread the syntheses. Only actual host tool outputs count as research actions.
