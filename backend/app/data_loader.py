import os
import re
import pandas as pd
from .db import get_conn

LEGACY_COLUMN_MAPPING = {
    "article_code": "Code",
    "authors": "Unnamed: 1",
    "year": "Unnamed: 2",
    "title": "Unnamed: 3",
    "venue": "Unnamed: 4",
    "doi": "Unnamed: 5",
    "url": "Unnamed: 6",
    "citation": "Unnamed: 7",
    "abstract": "Unnamed: 8",
    "categories": None,  # TODO: set column name when available
    "keywords": None,    # TODO: set column name when available
}

CODEBOOK_GROUPS = [
    ("EMI or CLIL?", "publication_types"),
    ("Research Topics", "journal_indices"),
    ("Research Results", "study_natures"),
    ("Participants", "education_levels"),
    ("Research Setting", "research_locations"),
    ("Research Methods", "research_focuses"),
]

DEFAULT_CODEBOOK_DEFINITIONS = {
    "publication_types": {
        "EMI": "Paper about EMI",
        "CLIL": "Paper about CLIL",
    },
    "journal_indices": {
        "TE1": "Teaching Materials, Textbooks",
        "TE2": "Teaching Issues (Teaching Approaches, Teaching Methods, Programs, Courses)",
        "TE3": "EMI, CLIL and CEFR",
        "TE4": "Assessment Issues",
        "TE5": "Contrasting CLIL vs EMI",
        "TE6": "Discussion of CLIL or EMI Definitions (not comparison against each other)",
        "TE7": "Policy Issues, including Rationale of why CLIL / EMI was adopted",
        "TE8": "Use of Multimedia/Digital/AI tools in EMI/CLIL teaching",
        "TE9": "Social issues caused by or that can affect EMI / CLIL policy",
        "DI1": "Classroom Discourse (Conversation Analytic -- CA -- Approach)",
        "DI2": "L1 Issues, Translanguaging; Code-switching; Code-mixing",
        "ELT1": "EMI / CLIL and ESP/EAP/TEFL",
        "ELT2": "Disciplinary literacy",
        "ELT3": "Team-teaching issues in EMI / CLIL",
        "TC1": '"In-service" Teacher Language Competence Issues/Testing',
        "TC2": '"Pre-service" Teacher Language Competence Issues/Testing',
        "TT1": '"In-service" Teacher-Training Issues and Outcome',
        "TT2": '"Pre-service" Teacher-Training Issues and Outcome',
    },
    "study_natures": {
        "OP1": "Pre-service Teachers' Opinions of EMI / CLIL (Teacher Trainees)",
        "OP2": "In-service Teachers' Opinions of EMI / CLIL, Teachers' Beliefs",
        "OP3": "Domestic Students' Opinions of EMI (excluding Pre-Service Teachers)",
        "OP4": "International Students' Opinions, Issues Related to International Students",
        "OP5": "Parents' Opinions of EMI",
        "OP6": "School leaders' / Administrators' Opinions of EMI",
        "OP7": "Outside reviewers / Program reviewers' Opinions",
        "OUT1": "Effects of EMI / CLIL on (English / Foreign) Language Learning",
        "OUT2": "Effects of EMI / CLIL on Identity issues",
        "OUT3": "Effets of EMI / CLIL on Affective Measures (e.g., attitude, motivation, happiness)",
        "OUT4": "Effects of EMI / CLIL on Content Learning (including teacher training courses)",
        "OUT5": "Effects of EMI / CLIL on Intercultural Competence",
    },
    "education_levels": {
        "ED1": "Pre K-12",
        "ED2": "Primary",
        "ED3": "Secondary",
        "ED4": "University all levels",
        "ED5": "Other education levels",
    },
    "research_locations": {
        "RS1": "Inner Circle -- US, Canada, UK, Ireland, Australia, New Zealand",
        "RS2": "Asia ESL -- Hong Kong, Singapore, Malaysia, Philippines, India, Pakistan, Bangladesh, Sri Lanka",
        "RS3": "Asia EFL -- countries not listed in Asia ESL",
        "RS4": "Middle East EFL -- Saudi Arabia, UAE, Qatar, Oman, Bahrain, Kuwait, Iran, Iraq, Jordan, Lebanon, Israel, Palestine, Syria, Yemen, Turkiye",
        "RS5": "Russia and Europe EFL -- countries other than Malta",
        "RS6": "Africa ESL (former British colonies) -- South Africa, Nigeria, Kenya, Ghana, Uganda, Tanzania, Rwanda, Zimbabwe, Botswana, Namibia, Zambia, Malawi, Cameroon, Liberia, Sierra Leone",
        "RS7": "North Africa EFL (Arabophone) -- Tunisia, Egype, Morocco, ALgeria, Libya, Mauritania, Sudan",
        "RS8": "Sub-Saharn Africa EFL (Francophone, Lusophone) -- Mozambique, Angola, Cape Verde, Senegal, Cote d'Ivoire, Burkina Faso, Mali, etc.",
        "RS9": "Central and South America EFL -- countries other than Guyana and Belize",
        "RS10": "Other ESL countries -- Caribbean and Oceania Anglophone nations, Malta, Guyana, Belize",
    },
    "research_focuses": {
        "EM1": "Studies that use Surveys and/or Interviews",
        "EM2": "Studies comparing results from more than one groups of participants",
        "EM3": "Studies in which pre-tests and post-tests are used",
        "EM4": "Studies that use Classroom Observation",
        "EM5": "Empirical papers that use research methods other than listed above",
        "NE1": "Literature Review",
        "NE2": "Editorial to special issues",
        "NE3": "Expert Opinion",
        "NE4": "Meta-Analysis",
        "NE5": "Other Non-Empirical Paper",
    },
}

LEGACY_METADATA_DEFINITIONS = {
    "publication_types": {"BC": "Book Chapter", "B": "Book", "JA": "Journal Article"},
    "journal_indices": {"SSCI": "SSCI", "AHCI": "A&HCI", "ESCI": "ESCI", "LLBA": "LLBA", "SCOPUS": "SCOPUS", "THSS": "THSS"},
    "study_natures": {"RE": "RE", "PD": "PD", "SQ": "SQ", "IN": "IN", "CO": "CO", "TS": "TS", "CS": "CS"},
    "education_levels": {"HE": "HE", "KS": "KS"},
    "research_locations": {"TW": "TW", "CN": "CN", "HK": "HK", "AS": "AS", "EU": "EU", "OTH": "OTH", "AR": "AR"},
    "research_focuses": {"TO": "TO", "SO": "SO", "EP": "EP", "EL": "EL", "CL": "CL", "TT": "TT", "CD": "CD", "TM": "TM", "RL": "RL", "SI": "SI", "RM": "RM"},
}

def clean_text(value):
    if value is None or pd.isna(value):
        return None
    text = str(value).replace("\xa0", " ").strip()
    return text

def clean_nullable_text(value):
    text = clean_text(value)
    if text == "":
        return None
    return text

def clean_doi(value):
    text = clean_nullable_text(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"x", "-", "nan", "none", "null"}:
        return None
    return text

def parse_year(value):
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None

def is_marked(value):
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in ["1", "1.0", "v", "y", "yes", "true", "x"]

def split_multi_values(value):
    text = clean_nullable_text(value)
    if not text:
        return []
    parts = [p.strip() for p in text.replace("；", ";").split(";")]
    return [p for p in parts if p]

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def load_codebook_definitions():
    codebook_path = os.getenv("CODEBOOK_PATH") or os.path.join(get_project_root(), "Final Codebook.xlsx")
    if not os.path.exists(codebook_path):
        return DEFAULT_CODEBOOK_DEFINITIONS

    try:
        df = pd.read_excel(codebook_path, header=None).fillna("")
    except Exception:
        return DEFAULT_CODEBOOK_DEFINITIONS

    by_heading = {heading: table for heading, table in CODEBOOK_GROUPS}
    definitions = {table: {} for _, table in CODEBOOK_GROUPS}
    current_table = None
    for _, row in df.iterrows():
        code = clean_nullable_text(row.iloc[0])
        description = clean_nullable_text(row.iloc[1])
        if not code:
            continue
        if code in by_heading:
            current_table = by_heading[code]
            continue
        if current_table and description:
            definitions[current_table][code] = description

    if any(definitions.values()):
        return definitions
    return DEFAULT_CODEBOOK_DEFINITIONS

def merge_metadata_definitions(primary, fallback):
    merged = {table: dict(tags) for table, tags in primary.items()}
    for table, tags in fallback.items():
        merged.setdefault(table, {})
        for code, desc in tags.items():
            merged[table].setdefault(code, desc)
    return merged

def normalize_columns(df):
    df = df.copy()
    df.columns = [clean_text(c) or "" for c in df.columns]
    return df

def read_sheet_with_detected_header(xls, sheet_name):
    header_candidates = [1, 4, 0]
    for header in header_candidates:
        df = normalize_columns(pd.read_excel(xls, sheet_name=sheet_name, header=header))
        cols = set(df.columns)
        if {"Paper ID", "Full APA Citation", "Research Paper Abstract"}.issubset(cols):
            return df, "actual"
        if {"Code", "Unnamed: 3"}.issubset(cols):
            return df, "legacy"
    return normalize_columns(pd.read_excel(xls, sheet_name=sheet_name, header=0)), "unknown"

def parse_year_from_citation(citation, article_code=None):
    for text in (citation, article_code):
        clean = clean_nullable_text(text)
        if not clean:
            continue
        match = re.search(r"(?:\(|\b)(19|20)\d{2}[a-z]?(?:\)|\b)", clean)
        if match:
            year_match = re.search(r"(19|20)\d{2}", match.group(0))
            if year_match:
                return int(year_match.group(0))
    return None

def extract_doi(citation):
    text = clean_nullable_text(citation)
    if not text:
        return None
    match = re.search(r"10\.\d{4,9}/[^\s,;]+", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).rstrip(").")

def parse_authors_from_citation(citation):
    text = clean_nullable_text(citation)
    if not text:
        return None
    match = re.match(r"^(.*?)\s*\((?:19|20)\d{2}[a-z]?\)", text)
    return clean_nullable_text(match.group(1)) if match else None

def parse_title_from_citation(citation):
    text = clean_nullable_text(citation)
    if not text:
        return None
    after_year = re.split(r"\((?:19|20)\d{2}[a-z]?\)\.\s*", text, maxsplit=1)
    if len(after_year) < 2:
        return None
    remainder = after_year[1]
    title = re.split(r"\.\s+", remainder, maxsplit=1)[0]
    return clean_nullable_text(title)

def build_row_values(row, data_format):
    if data_format == "actual":
        article_code = clean_nullable_text(row.get("Paper ID"))
        citation = clean_nullable_text(row.get("Full APA Citation"))
        title = parse_title_from_citation(citation) or article_code
        doi = extract_doi(citation)
        return {
            "article_code": article_code,
            "authors": parse_authors_from_citation(citation),
            "year": parse_year_from_citation(citation, article_code),
            "title": title,
            "venue": clean_nullable_text(row.get("Journal Quality")),
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else None,
            "citation": citation,
            "abstract": clean_nullable_text(row.get("Research Paper Abstract")),
            "categories_column": None,
            "keywords_column": None,
        }

    return {
        "article_code": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["article_code"])),
        "authors": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["authors"])),
        "year": parse_year(row.get(LEGACY_COLUMN_MAPPING["year"])),
        "title": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["title"])),
        "venue": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["venue"])),
        "doi": clean_doi(row.get(LEGACY_COLUMN_MAPPING["doi"])),
        "url": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["url"])),
        "citation": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["citation"])),
        "abstract": clean_nullable_text(row.get(LEGACY_COLUMN_MAPPING["abstract"])),
        "categories_column": LEGACY_COLUMN_MAPPING.get("categories"),
        "keywords_column": LEGACY_COLUMN_MAPPING.get("keywords"),
    }

def load_data(file_path):
    stats = {
        "ok": False,
        "total_rows": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "skipped_details": []
    }

    print(f"Loading data from {file_path}...")
    try:
        xls = pd.ExcelFile(file_path)
    except FileNotFoundError:
        stats["errors"].append({"sheet": "", "row": "", "error": f"File not found: {file_path}"})
        return stats
    except Exception as e:
        stats["errors"].append({"sheet": "", "row": "", "error": f"Invalid Excel file: {e}"})
        return stats

    conn = get_conn()
    conn.autocommit(False)

    try:
        with conn.cursor() as cursor:
            codebook_definitions = load_codebook_definitions()
            metadata_definitions = merge_metadata_definitions(codebook_definitions, LEGACY_METADATA_DEFINITIONS)

            # Pre-populate metadata tables.
            for table, tags in metadata_definitions.items():
                for code, desc in tags.items():
                    sql = f"""
                        INSERT INTO {table} (id, description)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE description = VALUES(description)
                    """
                    cursor.execute(sql, (code, desc))

            for sheet_name in xls.sheet_names:
                print(f"Processing sheet: {sheet_name}")
                df, data_format = read_sheet_with_detected_header(xls, sheet_name)

                categories_column = LEGACY_COLUMN_MAPPING.get("categories")
                keywords_column = LEGACY_COLUMN_MAPPING.get("keywords")
                supports_categories = categories_column and categories_column in df.columns
                supports_keywords = keywords_column and keywords_column in df.columns

                for index, row in df.iterrows():
                    stats["total_rows"] += 1
                    try:
                        values = build_row_values(row, data_format)
                        article_code = values["article_code"]
                        if not article_code:
                            stats["skipped"] += 1
                            stats["skipped_details"].append({"sheet": sheet_name, "row": int(index), "reason": "missing Paper ID/Code"})
                            continue

                        title = values["title"]
                        if not title:
                            stats["skipped"] += 1
                            stats["skipped_details"].append({"sheet": sheet_name, "row": int(index), "reason": "missing Title"})
                            continue

                        authors = values["authors"]
                        year = values["year"]
                        venue = values["venue"]
                        doi = values["doi"]
                        url = values["url"]
                        citation = values["citation"]
                        abstract = values["abstract"]

                        paper_id = None
                        cursor.execute("SELECT id FROM papers WHERE article_code = %s LIMIT 1", (article_code,))
                        found = cursor.fetchone()
                        if found:
                            paper_id = found["id"]

                        if paper_id is None and doi:
                            cursor.execute("SELECT id FROM papers WHERE doi = %s LIMIT 1", (doi,))
                            found = cursor.fetchone()
                            if found:
                                paper_id = found["id"]

                        if paper_id is None and year is not None:
                            cursor.execute("SELECT id FROM papers WHERE title = %s AND year = %s LIMIT 1", (title, year))
                            found = cursor.fetchone()
                            if found:
                                paper_id = found["id"]

                        if paper_id:
                            update_sql = """
                                UPDATE papers
                                SET title=%s, abstract=%s, year=%s, venue=%s, doi=%s, url=%s, authors=%s, article_code=%s, citation=%s
                                WHERE id=%s
                            """
                            cursor.execute(update_sql, (title, abstract, year, venue, doi, url, authors, article_code, citation, paper_id))
                            stats["updated"] += 1

                            join_tables = [
                                "paper_publication_types",
                                "paper_journal_indices",
                                "paper_study_natures",
                                "paper_education_levels",
                                "paper_research_locations",
                                "paper_research_focuses",
                            ]
                            if supports_categories:
                                join_tables.append("paper_categories")
                            if supports_keywords:
                                join_tables.append("paper_keywords")

                            for table in join_tables:
                                cursor.execute(f"DELETE FROM {table} WHERE paper_id = %s", (paper_id,))
                        else:
                            insert_sql = """
                                INSERT INTO papers (title, abstract, year, venue, doi, url, authors, article_code, citation)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(insert_sql, (title, abstract, year, venue, doi, url, authors, article_code, citation))
                            paper_id = cursor.lastrowid
                            stats["inserted"] += 1

                        def insert_tags(tag_dict, join_table, id_col):
                            for tag_code in tag_dict.keys():
                                if is_marked(row.get(tag_code)):
                                    sql_join = f"INSERT IGNORE INTO {join_table} (paper_id, {id_col}) VALUES (%s, %s)"
                                    cursor.execute(sql_join, (paper_id, tag_code))

                        insert_tags(metadata_definitions["publication_types"], "paper_publication_types", "publication_type_id")
                        insert_tags(metadata_definitions["journal_indices"], "paper_journal_indices", "journal_index_id")
                        insert_tags(metadata_definitions["study_natures"], "paper_study_natures", "study_nature_id")
                        insert_tags(metadata_definitions["education_levels"], "paper_education_levels", "education_level_id")
                        insert_tags(metadata_definitions["research_locations"], "paper_research_locations", "research_location_id")
                        insert_tags(metadata_definitions["research_focuses"], "paper_research_focuses", "research_focus_id")

                        if supports_categories:
                            for cat_name in split_multi_values(row.get(categories_column)):
                                cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (cat_name,))
                                cursor.execute("SELECT id FROM categories WHERE name = %s", (cat_name,))
                                cat = cursor.fetchone()
                                if cat:
                                    cursor.execute(
                                        "INSERT IGNORE INTO paper_categories (paper_id, category_id) VALUES (%s, %s)",
                                        (paper_id, cat["id"])
                                    )

                        if supports_keywords:
                            for kw_name in split_multi_values(row.get(keywords_column)):
                                cursor.execute("INSERT IGNORE INTO keywords (name) VALUES (%s)", (kw_name,))
                                cursor.execute("SELECT id FROM keywords WHERE name = %s", (kw_name,))
                                kw = cursor.fetchone()
                                if kw:
                                    cursor.execute(
                                        "INSERT IGNORE INTO paper_keywords (paper_id, keyword_id) VALUES (%s, %s)",
                                        (paper_id, kw["id"])
                                    )
                    except Exception as e:
                        stats["errors"].append({"sheet": sheet_name, "row": int(index), "error": str(e)})

                conn.commit()

        stats["ok"] = True
        print("Data loading complete.")
    except Exception as e:
        conn.rollback()
        stats["errors"].append({"sheet": "", "row": "", "error": str(e)})
    finally:
        conn.close()

    return stats

if __name__ == "__main__":
    DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "data.xlsx")
    load_data(DATA_PATH)
