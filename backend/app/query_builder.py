from typing import List, Optional, Tuple

# Build WHERE and params for search

def build_where(
    q: Optional[str],
    category_ids: Optional[List[int]],
    keyword_ids: Optional[List[int]],
    year_from: Optional[int],
    year_to: Optional[int],
    pub_type_ids: Optional[List[str]] = None,
    journal_ids: Optional[List[str]] = None,
    nature_ids: Optional[List[str]] = None,
    edu_ids: Optional[List[str]] = None,
    location_ids: Optional[List[str]] = None,
    focus_ids: Optional[List[str]] = None,
    field: str = "all",
) -> Tuple[str, list]:
    where = []
    params: list = []

    if q:
        # MySQL boolean mode; add * for prefix if user typed plain words
        tokens = [t.strip() for t in q.split() if t.strip()]
        boolean_q = " ".join(f"+{t}*" if t.isalnum() else t for t in tokens) or q
        
        if field == "title":
            where.append("MATCH(p.title) AGAINST (%s IN BOOLEAN MODE)")
            params.append(boolean_q)
        elif field == "abstract":
            where.append("MATCH(p.abstract) AGAINST (%s IN BOOLEAN MODE)")
            params.append(boolean_q)
        elif field == "author":
            where.append("MATCH(p.authors) AGAINST (%s IN BOOLEAN MODE)")
            params.append(boolean_q)
        else:
            # all
            where.append("(MATCH(p.title, p.abstract) AGAINST (%s IN BOOLEAN MODE) OR MATCH(p.authors) AGAINST (%s IN BOOLEAN MODE))")
            params.extend([boolean_q, boolean_q])

    if category_ids:
        for cid in category_ids:
            where.append("EXISTS (SELECT 1 FROM paper_categories pc WHERE pc.paper_id=p.id AND pc.category_id = %s)")
            params.append(int(cid))

    if keyword_ids:
        for kid in keyword_ids:
            where.append("EXISTS (SELECT 1 FROM paper_keywords pk WHERE pk.paper_id=p.id AND pk.keyword_id = %s)")
            params.append(int(kid))

    # New Filters
    if pub_type_ids:
        for pid in pub_type_ids:
            where.append("EXISTS (SELECT 1 FROM paper_publication_types ppt WHERE ppt.paper_id=p.id AND ppt.publication_type_id = %s)")
            params.append(pid)

    if journal_ids:
        for jid in journal_ids:
            where.append("EXISTS (SELECT 1 FROM paper_journal_indices pji WHERE pji.paper_id=p.id AND pji.journal_index_id = %s)")
            params.append(jid)

    if nature_ids:
        for nid in nature_ids:
            where.append("EXISTS (SELECT 1 FROM paper_study_natures psn WHERE psn.paper_id=p.id AND psn.study_nature_id = %s)")
            params.append(nid)

    if edu_ids:
        for eid in edu_ids:
            where.append("EXISTS (SELECT 1 FROM paper_education_levels pel WHERE pel.paper_id=p.id AND pel.education_level_id = %s)")
            params.append(eid)

    if location_ids:
        for lid in location_ids:
            where.append("EXISTS (SELECT 1 FROM paper_research_locations prl WHERE prl.paper_id=p.id AND prl.research_location_id = %s)")
            params.append(lid)
        
    if focus_ids:
        for fid in focus_ids:
            where.append("EXISTS (SELECT 1 FROM paper_research_focuses prf WHERE prf.paper_id=p.id AND prf.research_focus_id = %s)")
            params.append(fid)

    if year_from is not None:
        where.append("p.year >= %s")
        params.append(year_from)

    if year_to is not None:
        where.append("p.year <= %s")
        params.append(year_to)

    if where:
        sql = " WHERE " + " AND ".join(where)
        print(f"DEBUG SQL: {sql}")
        print(f"DEBUG PARAMS: {params}")
        return sql, params
    else:
        return "", params
