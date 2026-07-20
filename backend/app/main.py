import os
from fastapi import FastAPI, Query, UploadFile, File, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from .db import get_conn
from .query_builder import build_where
from .data_loader import load_data

app = FastAPI(title="EMI Literature DB API", version="0.1.0")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
ADMIN_UPLOAD_TOKEN = os.getenv("ADMIN_UPLOAD_TOKEN", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Paper(BaseModel):
    id: int
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    authors: Optional[str] = None
    journal_quality: Optional[str] = None


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[Paper]


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/admin/upload-excel")
async def upload_excel(
    file: UploadFile = File(...),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    if not ADMIN_UPLOAD_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_UPLOAD_TOKEN is not configured")
    if x_admin_token != ADMIN_UPLOAD_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    saved_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    try:
        result = load_data(saved_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {e}")

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"message": "Import failed", "result": result})

    result["filename"] = safe_name
    return result


@app.get("/categories")
def categories():
    sql = "SELECT id, name FROM categories ORDER BY name"
    with get_conn() as conn, conn.cursor() as c:
        c.execute(sql)
        return c.fetchall()


@app.get("/keywords")
def keywords():
    sql = "SELECT id, name FROM keywords ORDER BY name"
    with get_conn() as conn, conn.cursor() as c:
        c.execute(sql)
        return c.fetchall()


@app.get("/facets")
def facets(q: Optional[str] = None,
           category_ids: Optional[List[int]] = Query(default=None),
           keyword_ids: Optional[List[int]] = Query(default=None),
           year_from: Optional[int] = None,
           year_to: Optional[int] = None,
           pub_type_ids: Optional[List[str]] = Query(default=None),
           journal_ids: Optional[List[str]] = Query(default=None),
           nature_ids: Optional[List[str]] = Query(default=None),
           edu_ids: Optional[List[str]] = Query(default=None),
           location_ids: Optional[List[str]] = Query(default=None),
           focus_ids: Optional[List[str]] = Query(default=None),
           field: str = "all"):
    """Facet counts under current filter (for dynamic checkboxes)."""
    where, params = build_where(q, category_ids, keyword_ids, year_from, year_to, 
                                pub_type_ids, journal_ids, nature_ids, edu_ids, location_ids, focus_ids, field)

    # Convert WHERE clause to ON clause for LEFT JOIN to keep all facets visible
    join_condition = ""
    if where:
        # Strip " WHERE " and add "AND"
        join_condition = "AND " + where[7:]

    def get_facet_sql(table, join_table, id_col, name_col='id'):
        # name_col defaults to 'id' because our new tables use the code as the ID and don't have a separate name column yet (or we use id as name)
        # Actually schema has 'description' but we stored code in 'id'.
        # Let's select id and description (if available) or just id.
        # Our schema: id, description.
        return f"""
        SELECT t.id, t.description as name, COUNT(p.id) AS cnt
        FROM {table} t
        LEFT JOIN {join_table} jt ON jt.{id_col} = t.id
        LEFT JOIN papers p ON p.id = jt.paper_id {join_condition}
        GROUP BY t.id, t.description
        HAVING cnt > 0
        ORDER BY t.id
        LIMIT 100
        """

    # category facet
    cat_sql = f"""
    SELECT c.id, c.name, COUNT(p.id) AS cnt
    FROM categories c
    LEFT JOIN paper_categories pc ON pc.category_id = c.id
    LEFT JOIN papers p ON p.id = pc.paper_id {join_condition}
    GROUP BY c.id, c.name
    HAVING cnt > 0
    ORDER BY cnt DESC, c.name
    LIMIT 50
    """
    # keyword facet
    kw_sql = f"""
    SELECT k.id, k.name, COUNT(p.id) AS cnt
    FROM keywords k
    LEFT JOIN paper_keywords pk ON pk.keyword_id = k.id
    LEFT JOIN papers p ON p.id = pk.paper_id {join_condition}
    GROUP BY k.id, k.name
    HAVING cnt > 0
    ORDER BY cnt DESC, k.name
    LIMIT 50
    """
    
    with get_conn() as conn, conn.cursor() as c:
        # Helper to execute and fetch
        def fetch_facet(sql, p):
            c.execute(sql, p)
            return c.fetchall()

        cats = fetch_facet(cat_sql, params)
        kws = fetch_facet(kw_sql, params)
        
        pub_types = fetch_facet(get_facet_sql('publication_types', 'paper_publication_types', 'publication_type_id'), params)
        journals = fetch_facet(get_facet_sql('journal_indices', 'paper_journal_indices', 'journal_index_id'), params)
        natures = fetch_facet(get_facet_sql('study_natures', 'paper_study_natures', 'study_nature_id'), params)
        edus = fetch_facet(get_facet_sql('education_levels', 'paper_education_levels', 'education_level_id'), params)
        locations = fetch_facet(get_facet_sql('research_locations', 'paper_research_locations', 'research_location_id'), params)
        focuses = fetch_facet(get_facet_sql('research_focuses', 'paper_research_focuses', 'research_focus_id'), params)

    return {
        "categories": cats, 
        "keywords": kws,
        "pub_types": pub_types,
        "journals": journals,
        "natures": natures,
        "edus": edus,
        "locations": locations,
        "focuses": focuses
    }


@app.get("/search", response_model=SearchResponse)
def search(
    q: Optional[str] = None,
    category_ids: Optional[List[int]] = Query(default=None),
    keyword_ids: Optional[List[int]] = Query(default=None),
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    pub_type_ids: Optional[List[str]] = Query(default=None),
    journal_ids: Optional[List[str]] = Query(default=None),
    nature_ids: Optional[List[str]] = Query(default=None),
    edu_ids: Optional[List[str]] = Query(default=None),
    location_ids: Optional[List[str]] = Query(default=None),
    focus_ids: Optional[List[str]] = Query(default=None),
    field: str = "all",
    sort: str = "relevance",  # or "year_desc", "year_asc"
    page: int = 1,
    page_size: int = 10,
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size

    where, params = build_where(q, category_ids, keyword_ids, year_from, year_to,
                                pub_type_ids, journal_ids, nature_ids, edu_ids, location_ids, focus_ids, field)

    if sort == "year_desc":
        order_by = "ORDER BY (p.year IS NULL), p.year DESC, p.id DESC"
    elif sort == "year_asc":
        order_by = "ORDER BY (p.year IS NULL), p.year ASC, p.id ASC"
    else:
        # Relevance: if no q, fallback to recent
        if q:
            order_by = "ORDER BY relevance DESC, p.year DESC"
        else:
            order_by = "ORDER BY p.year DESC, p.id DESC"

    # count
    count_sql = f"SELECT COUNT(*) AS cnt FROM papers p {where}"

    # Determine relevance column based on field
    if not q:
        relevance_col = "0"
    elif field == "title":
        relevance_col = "MATCH(p.title) AGAINST (%s IN BOOLEAN MODE)"
    elif field == "abstract":
        relevance_col = "MATCH(p.abstract) AGAINST (%s IN BOOLEAN MODE)"
    elif field == "author":
        relevance_col = "MATCH(p.authors) AGAINST (%s IN BOOLEAN MODE)"
    else:
        relevance_col = "(MATCH(p.title, p.abstract) AGAINST (%s IN BOOLEAN MODE) OR MATCH(p.authors) AGAINST (%s IN BOOLEAN MODE))"

    # search
    select_sql = f"""
    SELECT p.*, 
           {relevance_col} AS relevance
    FROM papers p
    {where}
    {order_by}
    LIMIT %s OFFSET %s
    """

    with get_conn() as conn, conn.cursor() as c:
        c.execute(count_sql, params)
        total = c.fetchone()["cnt"]

        sel_params = params.copy()
        if q:
            # add AGAINST param for SELECT relevance
            tokens = [t.strip() for t in q.split() if t.strip()]
            boolean_q = " ".join(f"+{t}*" if t.isalnum() else t for t in tokens) or q
            
            if field == "all":
                sel_params = [boolean_q, boolean_q] + sel_params
            else:
                sel_params = [boolean_q] + sel_params
                
        sel_params += [page_size, offset]

        c.execute(select_sql, sel_params)
        rows = c.fetchall()

    items = [Paper(**row) for row in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}
