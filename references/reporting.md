# V3.1 Chinese review implementation

Read the complete user specification at references/report-output-spec-v3.1.md through the skill's resource interface. It is authoritative for narrative and bibliography. Keep the DOCX as a compressed scholarly review, with an overall answer, scientific comparisons, and a final synthesis.

## Structure and Word hierarchy

Map the single document title to Word Title. Map the specification's H2 major chapters to Word Heading 1 and its H3 subthemes to Word Heading 2. Generate chapter numbers automatically; do not put numbering in draft titles. Do not use Word Heading 3/4, a numbered TL;DR, separate scope/audit modules, or a standalone chapter for each paper.

The draft sections are introduction, overview, one to four theme chapters, limitations, conclusion, in that order. Overview and limitations are part of the 3-6 body chapters. Their names are topic-specific. Introduction is titled 引言 and the final numbered chapter 结论与展望. The final unnumbered heading is 参考文献.

TL;DR answers object, overall state, 3-5 important advances where evidence supports them, main limits, and the reader's takeaway. Introduction covers object/value, principles/history, current routes, the central bottleneck, and scope/roadmap. Conclusion recombines field state, the most reliable scientific insights, 2-4 decisive unresolved issues, and grounded future work. Body openings establish a judgment before studies; closings integrate rather than repeat.

## Citations and access

Place claim_ids on individual spans when a paragraph contains different facts, data, or evidence tiers. Whole-paragraph claim_ids are suitable for a single synthesis claim. The renderer orders works by first appearance, merges same-paper sources, and creates baseline bracketed groups. Do not type reference numbers into prose.

Use paper metadata authors (or verified authors_acs), venue (or verified journal_abbreviation), year, volume, pages or article_number, and doi. The renderer supplies native italic/bold emphasis. An existing DOI takes priority over a page URL. Web records use an ISO access date. Unavailable fields are omitted and recorded in report_citations.json; fetch public authoritative metadata during browsing if possible, never invent fields to complete the style.

A source may be important despite having only an abstract. Explain material abstract/index/version boundaries in the relevant prose, not through extra chapters. Different page URLs for one paper remain one work; all supporting URLs and their tiers stay in the audit.

## Length and semantic QA

For a full report, target 6000-12000 Chinese characters, TL;DR 400-800, introduction about 8-12%, conclusion about 6-10%, normally 2-4 useful tables. Body opening/closing paragraphs are normally 150-300 characters; ordinary paragraphs about 150-400. These are writing targets, not padding quotas. Short/evidence-limited cases require an explicit reason. The default full profile enforces the full-report and TL;DR length ranges. Use user_concise/user_custom only for an explicit user length request, or evidence_limited for an actual limitation, with a recorded reason. Other proportional/table targets generate editorial warnings. Never pad or invent content to make a gate pass.

Use narrative_plan.json before writing and editorial_review.json after rereading. All 19 checklist items need specific bases. A LIMITED item needs a visible limitation; FAIL/PENDING blocks final output. Passing structural checks cannot certify synthesis, comparison, evidence strength, or continuous readability. Review those substantively.

The paired literature_map.csv and research_audit.zip retain the former V3 audit functionality, including route counts, saturation denominator, source tiers, anchor changes and failures. No audit appendix is injected into the review DOCX. Do not include the internal plan or checklist in the report unless asked.

Render the final DOCX and inspect every page for missing glyphs, orphaned headings, table breaks, citation placement and reference typography. Keep the established Letter page size and readable Chinese/Latin type, black headings, restrained tables, and no decorative title border.
