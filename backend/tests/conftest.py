import os
import sys
import importlib
from pathlib import Path

import pandas as pd
import pymysql
import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = FIXTURES_DIR / "test_emi_articles.xlsx"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DB_NAME = os.getenv("TEST_DB_NAME", "emi_test_db")
TEST_DB_HOST = os.getenv("TEST_DB_HOST", os.getenv("DB_HOST", "localhost"))
TEST_DB_PORT = int(os.getenv("TEST_DB_PORT", os.getenv("DB_PORT", "3306")))
TEST_DB_USER = os.getenv("TEST_DB_USER", "root")
TEST_DB_PASSWORD = os.getenv("TEST_DB_PASSWORD", "rootpass")
TEST_ADMIN_TOKEN = os.getenv("TEST_ADMIN_TOKEN", "test-token")

ENV_DB_NAME = os.getenv("DB_NAME")
if TEST_DB_NAME != "emi_test_db":
    raise SystemExit("Tests require TEST_DB_NAME to be emi_test_db")
if ENV_DB_NAME and ENV_DB_NAME != "emi_test_db":
    raise SystemExit("Tests require DB_NAME to be emi_test_db to avoid touching production data")

BASE_COLUMNS = [
    "Code",
    "Unnamed: 1",
    "Unnamed: 2",
    "Unnamed: 3",
    "Unnamed: 4",
    "Unnamed: 5",
    "Unnamed: 6",
    "Unnamed: 7",
    "Unnamed: 8",
]

METADATA_COLUMNS = [
    "BC", "B", "JA",
    "SSCI", "AHCI", "ESCI", "LLBA", "SCOPUS", "THSS",
    "RE", "PD", "SQ", "IN", "CO", "TS", "CS",
    "HE", "KS",
    "TW", "CN", "HK", "AS", "EU", "OTH", "AR",
    "TO", "SO", "EP", "EL", "CL", "TT", "CD", "TM", "RL", "SI", "RM",
]

ALL_COLUMNS = BASE_COLUMNS + METADATA_COLUMNS


def _set_env(upload_dir):
    os.environ["DB_HOST"] = TEST_DB_HOST
    os.environ["DB_PORT"] = str(TEST_DB_PORT)
    os.environ["DB_USER"] = TEST_DB_USER
    os.environ["DB_PASSWORD"] = TEST_DB_PASSWORD
    os.environ["DB_NAME"] = TEST_DB_NAME
    os.environ["ADMIN_UPLOAD_TOKEN"] = TEST_ADMIN_TOKEN
    os.environ["UPLOAD_DIR"] = str(upload_dir)


def build_row(code, title, year, doi, marks, authors="Test Author", venue="Test Journal", url="https://example.com", citation="Test Citation", abstract=""):
    row = {col: "" for col in ALL_COLUMNS}
    row["Code"] = code
    row["Unnamed: 1"] = authors
    row["Unnamed: 2"] = year
    row["Unnamed: 3"] = title
    row["Unnamed: 4"] = venue
    row["Unnamed: 5"] = doi
    row["Unnamed: 6"] = url
    row["Unnamed: 7"] = citation
    row["Unnamed: 8"] = abstract
    for col in marks:
        row[col] = "1"
    return row


def write_excel(path, rows, sheet_name="Sheet1"):
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=ALL_COLUMNS)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=4)
        ws = writer.sheets[sheet_name]
        for i in range(1, 5):
            ws.cell(row=i, column=1, value="NOTE")


def ensure_fixture_file():
    if not FIXTURE_PATH.exists():
        rows = [
            build_row(
                "T001",
                "EMI Policy in Higher Education",
                2020,
                "10.1000/test001",
                ["JA", "SSCI", "HE", "TW", "TO"],
                abstract="Policy discussion in higher education."
            ),
            build_row(
                "T002",
                "Student Experiences in EMI Classrooms",
                2021.0,
                "x",
                ["JA", "SCOPUS", "HE", "AS", "SO"],
                abstract="Experiences in EMI classrooms."
            ),
            build_row(
                "T003",
                "Teacher Beliefs and EMI Pedagogy",
                "2022",
                "-",
                ["JA", "ESCI", "HE", "EU", "TT"],
                abstract="Teacher beliefs about EMI pedagogy."
            ),
        ]
        write_excel(FIXTURE_PATH, rows)


@pytest.fixture(scope="session")
def app_modules(tmp_path_factory):
    upload_dir = tmp_path_factory.mktemp("uploads")
    _set_env(upload_dir)

    import app.db
    import app.data_loader
    import app.main

    importlib.reload(app.db)
    importlib.reload(app.data_loader)
    importlib.reload(app.main)

    return {
        "db": app.db,
        "data_loader": app.data_loader,
        "main": app.main,
    }


def _run_schema(cursor, schema_sql):
    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
    for statement in statements:
        cursor.execute(statement)


def _ensure_column(cursor, table, column, col_type):
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.columns WHERE table_schema=%s AND table_name=%s AND column_name=%s",
        (TEST_DB_NAME, table, column)
    )
    if cursor.fetchone()["cnt"] == 0:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def _ensure_index(cursor, table, index_name, index_def):
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.statistics WHERE table_schema=%s AND table_name=%s AND index_name=%s",
        (TEST_DB_NAME, table, index_name)
    )
    if cursor.fetchone()["cnt"] == 0:
        cursor.execute(f"ALTER TABLE {table} ADD {index_def}")


@pytest.fixture(scope="session", autouse=True)
def init_test_db(app_modules):
    schema_path = ROOT_DIR / "mysql" / "init" / "01_schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    schema_sql = schema_sql.replace("emi_db", TEST_DB_NAME)

    conn = pymysql.connect(
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        database="mysql",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
            cursor.execute(f"CREATE DATABASE {TEST_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            _run_schema(cursor, schema_sql)

            cursor.execute(f"USE {TEST_DB_NAME}")
            _ensure_column(cursor, "papers", "article_code", "VARCHAR(50)")
            _ensure_column(cursor, "papers", "citation", "TEXT")
            _ensure_index(cursor, "papers", "uk_papers_article_code", "UNIQUE KEY uk_papers_article_code (article_code)")
            _ensure_index(cursor, "papers", "idx_papers_doi", "INDEX idx_papers_doi (doi)")
            _ensure_index(cursor, "papers", "idx_papers_title_year", "INDEX idx_papers_title_year (title, year)")

    yield


@pytest.fixture(autouse=True)
def clean_test_db():
    conn = pymysql.connect(
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        database=TEST_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    tables = [
        "paper_publication_types",
        "paper_journal_indices",
        "paper_study_natures",
        "paper_education_levels",
        "paper_research_locations",
        "paper_research_focuses",
        "paper_categories",
        "paper_keywords",
        "papers",
        "publication_types",
        "journal_indices",
        "study_natures",
        "education_levels",
        "research_locations",
        "research_focuses",
        "categories",
        "keywords",
    ]
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in tables:
                cursor.execute(f"TRUNCATE TABLE {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    yield


@pytest.fixture
def db_conn():
    conn = pymysql.connect(
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        user=TEST_DB_USER,
        password=TEST_DB_PASSWORD,
        database=TEST_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def excel_fixture_path():
    ensure_fixture_file()
    return FIXTURE_PATH


@pytest.fixture
def admin_token():
    return TEST_ADMIN_TOKEN
