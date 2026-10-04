# Discovery and citation tracing

Maintain the original six research capabilities while running one autonomous project. Record each transformation of a candidate into a screened paper, anchor, evidence item, or cited conclusion. A new user request after delivery starts another research round; a checkpoint during one run does not request user confirmation.

## Scope and queries

Write question_decomposition.json with the question, interpreted alternatives, inclusion/exclusion, subquestions, scientific dimensions, and assumptions. Do not infer that an absent date limit excludes foundational work. If "recent" is requested, put special weight on the current window but follow earlier anchor and citation chains.

Build query_families.json with broad, narrow, synonym, method, application, platform, citation, recent, review, and counterfactual families. Mark a genuinely irrelevant family NOT_APPLICABLE with a concrete reason. A counterfactual query deliberately avoids the current core vocabulary while expressing the same scientific problem. Query outputs must name the parent subquestion, family, route, source, round, actual query string, tool result count seen, paper IDs, status, and failure reason. Store them in retrieval_ledger.jsonl as soon as returned, including failed and empty attempts. Web result counts are observed results, never the search engine's approximate total.

Search a range of publisher pages, repositories, database records, review bibliographies, and openly displayed citations through host web tools. Count genuinely different routes, not merely repeated queries on one search engine. Batch independent web requests where appropriate; make follow-up queries after inspecting current gaps.

## Screening and expansion

Normalize identifiers in this order: exact DOI, recognized database ID, exact normalized title, and cautious title/first-author/year matching. Conflicting DOIs or different study designs require separate records or an explicit version link, not automatic merger. Keep all query IDs, URLs, routes, round numbers, and version links.

Screen title and abstract with include, likely_include, uncertain, likely_exclude, exclude. Set a reason and confidence. Preserve recent, low-citation, nonstandard terminology, closed and unknown-access records in the candidate set. Scientific importance, access/read depth, and literature role have distinct fields. Select diverse seeds from different clusters, dates, research groups, methods, venues, applications, and influence levels.

Expand via backward references, forward citing works, related/semantic pages, reviews, authors/groups, latest articles, and newly learned terms. Label a route completed, partial, unavailable, or not applicable. For every subquestion, update terminology, primary-paper coverage, latest paper coverage, citation-path coverage, competing findings, missing direct evidence, and targeted next search. Protect against vocabulary islands and query drift. Keep uncertain candidates visible in the map.

## Anchor audit and stopping

For each major subquestion stress test anchors via backward references, forward citations, related papers, recent review references, exact method/system/acronym searches, and competing-anchor searches. Record the query, status, candidates, why a candidate is more direct, and any replacement. Evaluate direct relevance, primary evidence, method/system fit, experimental completeness, novelty, recency, influence, and representativeness. Citation count stays low-weight; an OA flag cannot boost importance.

Retrieval and concept saturation are separate judgments. A saturated run requires all applicable query families, keyword/backward/forward/related/recent paths, no important coverage gap, a completed anchor audit, and at least two distinct consecutive low-novelty rounds with no new core paper, concept cluster, contradiction, or critical term. Use the actual de-duplicated candidate denominator and record the threshold, normally 5%. A round without a usable denominator cannot satisfy a numeric threshold. Cached repeats of identical query/route/source cannot create qualifying rounds. Search/tool failure or an unexecuted route cannot masquerade as low novelty.

When time, tool access, or budget prevents the gate, finish as COMPLETED_WITH_LIMITATIONS and explain the missing routes. Do not claim exhaustive recall or convert process coverage to estimated percentage of all papers in the field.

The local evaluator is conservative and uses supplied structured ledger data. The scientist/agent must still inspect whether terms, methods and contradictory results were genuinely covered. Scientific interpretation never follows from a metadata count alone.
