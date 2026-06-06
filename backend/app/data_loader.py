import os
import pandas as pd
from .db import get_conn

COLUMN_MAPPING = {
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

metadata_definitions = {
    "publication_types": {
        "BC": "Book Chapter", "B": "Book", "JA": "Journal Article"
    },
    "journal_indices": {
        "SSCI": "SSCI", "AHCI": "A&HCI", "ESCI": "ESCI", "LLBA": "LLBA", "SCOPUS": "SCOPUS", "THSS": "THSS"
    },
    "study_natures": {
        "RE": "RE", "PD": "PD", "SQ": "SQ", "IN": "IN", "CO": "CO", "TS": "TS", "CS": "CS"
    },
    "education_levels": {
        "HE": "HE", "KS": "KS"
    },
    "research_locations": {
        "TW": "TW", "CN": "CN", "HK": "HK", "AS": "AS", "EU": "EU", "OTH": "OTH", "AR": "AR"
    },
    "research_focuses": {
        "TO": "TO", "SO": "SO", "EP": "EP", "EL": "EL", "CL": "CL", "TT": "TT", "CD": "CD", "TM": "TM", "RL": "RL", "SI": "SI", "RM": "RM"
    }
}

def clean_text(value):
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
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
            # Pre-populate metadata tables
            for table, tags in metadata_definitions.items():
                for code, desc in tags.items():
                    sql = f"INSERT IGNORE INTO {table} (id, description) VALUES (%s, %s)"
                    cursor.execute(sql, (code, desc))

            for sheet_name in xls.sheet_names:
                print(f"Processing sheet: {sheet_name}")
                df = pd.read_excel(xls, sheet_name=sheet_name, header=4)

                categories_column = COLUMN_MAPPING.get("categories")
                keywords_column = COLUMN_MAPPING.get("keywords")
                supports_categories = categories_column and categories_column in df.columns
                supports_keywords = keywords_column and keywords_column in df.columns

                for index, row in df.iterrows():
                    stats["total_rows"] += 1
                    try:
                        article_code = clean_nullable_text(row.get(COLUMN_MAPPING["article_code"]))
                        if not article_code:
                            stats["skipped"] += 1
                            stats["skipped_details"].append({"sheet": sheet_name, "row": int(index), "reason": "missing Code"})
                            continue

                        title = clean_nullable_text(row.get(COLUMN_MAPPING["title"]))
                        if not title:
                            stats["skipped"] += 1
                            stats["skipped_details"].append({"sheet": sheet_name, "row": int(index), "reason": "missing Title"})
                            continue

                        authors = clean_nullable_text(row.get(COLUMN_MAPPING["authors"]))
                        year = parse_year(row.get(COLUMN_MAPPING["year"]))
                        venue = clean_nullable_text(row.get(COLUMN_MAPPING["venue"]))
                        doi = clean_doi(row.get(COLUMN_MAPPING["doi"]))
                        url = clean_nullable_text(row.get(COLUMN_MAPPING["url"]))
                        citation = clean_nullable_text(row.get(COLUMN_MAPPING["citation"]))
                        abstract = clean_nullable_text(row.get(COLUMN_MAPPING["abstract"]))

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
