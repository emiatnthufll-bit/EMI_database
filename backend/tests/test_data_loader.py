import pandas as pd


def test_first_import(app_modules, excel_fixture_path, db_conn):
    load_data = app_modules["data_loader"].load_data
    result = load_data(str(excel_fixture_path))

    assert result["ok"] is True
    assert result["total_rows"] >= 3
    assert result["inserted"] == 3
    assert result["updated"] == 0
    assert result["errors"] == []

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM papers")
        assert cursor.fetchone()["cnt"] == 3
        cursor.execute("SELECT article_code FROM papers")
        codes = {row["article_code"] for row in cursor.fetchall()}
        assert codes == {"T001", "T002", "T003"}


def test_repeat_import_no_dup(app_modules, excel_fixture_path, db_conn):
    load_data = app_modules["data_loader"].load_data
    load_data(str(excel_fixture_path))
    second = load_data(str(excel_fixture_path))

    assert second["inserted"] == 0
    assert second["updated"] >= 1

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM papers")
        assert cursor.fetchone()["cnt"] == 3


def test_update_import(app_modules, excel_fixture_path, db_conn, tmp_path):
    load_data = app_modules["data_loader"].load_data
    load_data(str(excel_fixture_path))

    rows = [
        {
            "Code": "T001",
            "Unnamed: 1": "Test Author",
            "Unnamed: 2": 2020,
            "Unnamed: 3": "Updated EMI Policy in Higher Education",
            "Unnamed: 4": "Test Journal",
            "Unnamed: 5": "10.1000/test001",
            "Unnamed: 6": "https://example.com",
            "Unnamed: 7": "Updated Citation",
            "Unnamed: 8": "Updated abstract content.",
            "JA": "1",
            "SSCI": "1",
            "HE": "1",
            "TW": "1",
            "TO": "1",
        }
    ]
    columns = [
        "Code", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6", "Unnamed: 7", "Unnamed: 8",
        "BC", "B", "JA",
        "SSCI", "AHCI", "ESCI", "LLBA", "SCOPUS", "THSS",
        "RE", "PD", "SQ", "IN", "CO", "TS", "CS",
        "HE", "KS",
        "TW", "CN", "HK", "AS", "EU", "OTH", "AR",
        "TO", "SO", "EP", "EL", "CL", "TT", "CD", "TM", "RL", "SI", "RM",
    ]

    df = pd.DataFrame(rows, columns=columns)
    updated_path = tmp_path / "updated.xlsx"
    with pd.ExcelWriter(updated_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False, startrow=4)
        ws = writer.sheets["Sheet1"]
        for i in range(1, 5):
            ws.cell(row=i, column=1, value="NOTE")

    result = load_data(str(updated_path))
    assert result["updated"] >= 1

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT title, abstract FROM papers WHERE article_code = %s", ("T001",))
        row = cursor.fetchone()
        assert row["title"] == "Updated EMI Policy in Higher Education"
        assert row["abstract"] == "Updated abstract content."


def test_doi_cleanup(app_modules, db_conn, tmp_path):
    load_data = app_modules["data_loader"].load_data

    rows = []
    dois = ["x", "X", "-", "", None, "nan", "none", "null"]
    for i, doi in enumerate(dois):
        rows.append({
            "Code": f"D00{i}",
            "Unnamed: 1": "Author",
            "Unnamed: 2": 2020,
            "Unnamed: 3": f"Title {i}",
            "Unnamed: 4": "Journal",
            "Unnamed: 5": doi,
            "Unnamed: 6": "https://example.com",
            "Unnamed: 7": "Citation",
            "Unnamed: 8": "Abstract",
            "JA": "1",
        })

    columns = [
        "Code", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6", "Unnamed: 7", "Unnamed: 8",
        "BC", "B", "JA",
        "SSCI", "AHCI", "ESCI", "LLBA", "SCOPUS", "THSS",
        "RE", "PD", "SQ", "IN", "CO", "TS", "CS",
        "HE", "KS",
        "TW", "CN", "HK", "AS", "EU", "OTH", "AR",
        "TO", "SO", "EP", "EL", "CL", "TT", "CD", "TM", "RL", "SI", "RM",
    ]

    df = pd.DataFrame(rows, columns=columns)
    path = tmp_path / "doi.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False, startrow=4)
        ws = writer.sheets["Sheet1"]
        for i in range(1, 5):
            ws.cell(row=i, column=1, value="NOTE")

    result = load_data(str(path))
    assert result["ok"] is True

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT doi FROM papers ORDER BY article_code")
        for row in cursor.fetchall():
            assert row["doi"] is None


def test_year_parsing(app_modules, db_conn, tmp_path):
    load_data = app_modules["data_loader"].load_data

    rows = [
        {"Code": "Y001", "Unnamed: 1": "Author", "Unnamed: 2": 2020, "Unnamed: 3": "Title 1", "Unnamed: 4": "Journal", "Unnamed: 5": "10.1/y1", "Unnamed: 6": "https://example.com", "Unnamed: 7": "Citation", "Unnamed: 8": "Abstract", "JA": "1"},
        {"Code": "Y002", "Unnamed: 1": "Author", "Unnamed: 2": 2021.0, "Unnamed: 3": "Title 2", "Unnamed: 4": "Journal", "Unnamed: 5": "10.1/y2", "Unnamed: 6": "https://example.com", "Unnamed: 7": "Citation", "Unnamed: 8": "Abstract", "JA": "1"},
        {"Code": "Y003", "Unnamed: 1": "Author", "Unnamed: 2": "2022", "Unnamed: 3": "Title 3", "Unnamed: 4": "Journal", "Unnamed: 5": "10.1/y3", "Unnamed: 6": "https://example.com", "Unnamed: 7": "Citation", "Unnamed: 8": "Abstract", "JA": "1"},
        {"Code": "Y004", "Unnamed: 1": "Author", "Unnamed: 2": "invalid", "Unnamed: 3": "Title 4", "Unnamed: 4": "Journal", "Unnamed: 5": "10.1/y4", "Unnamed: 6": "https://example.com", "Unnamed: 7": "Citation", "Unnamed: 8": "Abstract", "JA": "1"},
    ]

    columns = [
        "Code", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6", "Unnamed: 7", "Unnamed: 8",
        "BC", "B", "JA",
        "SSCI", "AHCI", "ESCI", "LLBA", "SCOPUS", "THSS",
        "RE", "PD", "SQ", "IN", "CO", "TS", "CS",
        "HE", "KS",
        "TW", "CN", "HK", "AS", "EU", "OTH", "AR",
        "TO", "SO", "EP", "EL", "CL", "TT", "CD", "TM", "RL", "SI", "RM",
    ]

    df = pd.DataFrame(rows, columns=columns)
    path = tmp_path / "year.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False, startrow=4)
        ws = writer.sheets["Sheet1"]
        for i in range(1, 5):
            ws.cell(row=i, column=1, value="NOTE")

    result = load_data(str(path))
    assert result["ok"] is True

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT article_code, year FROM papers ORDER BY article_code")
        rows = cursor.fetchall()
        year_map = {row["article_code"]: row["year"] for row in rows}
        assert year_map["Y001"] == 2020
        assert year_map["Y002"] == 2021
        assert year_map["Y003"] == 2022
        assert year_map["Y004"] is None


def test_missing_code_or_title(app_modules, db_conn, tmp_path):
    load_data = app_modules["data_loader"].load_data

    rows = [
        {"Code": "", "Unnamed: 1": "Author", "Unnamed: 2": 2020, "Unnamed: 3": "Title 1", "Unnamed: 4": "Journal", "Unnamed: 5": "10.1/m1", "Unnamed: 6": "https://example.com", "Unnamed: 7": "Citation", "Unnamed: 8": "Abstract", "JA": "1"},
        {"Code": "M002", "Unnamed: 1": "Author", "Unnamed: 2": 2020, "Unnamed: 3": "", "Unnamed: 4": "Journal", "Unnamed: 5": "10.1/m2", "Unnamed: 6": "https://example.com", "Unnamed: 7": "Citation", "Unnamed: 8": "Abstract", "JA": "1"},
    ]

    columns = [
        "Code", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6", "Unnamed: 7", "Unnamed: 8",
        "BC", "B", "JA",
        "SSCI", "AHCI", "ESCI", "LLBA", "SCOPUS", "THSS",
        "RE", "PD", "SQ", "IN", "CO", "TS", "CS",
        "HE", "KS",
        "TW", "CN", "HK", "AS", "EU", "OTH", "AR",
        "TO", "SO", "EP", "EL", "CL", "TT", "CD", "TM", "RL", "SI", "RM",
    ]

    df = pd.DataFrame(rows, columns=columns)
    path = tmp_path / "missing.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False, startrow=4)
        ws = writer.sheets["Sheet1"]
        for i in range(1, 5):
            ws.cell(row=i, column=1, value="NOTE")

    result = load_data(str(path))
    assert result["skipped"] == 2

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS cnt FROM papers")
        assert cursor.fetchone()["cnt"] == 0


def test_metadata_relations(app_modules, excel_fixture_path, db_conn):
    load_data = app_modules["data_loader"].load_data
    load_data(str(excel_fixture_path))

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM papers WHERE article_code = %s", ("T001",))
        paper_id = cursor.fetchone()["id"]

        cursor.execute("SELECT publication_type_id FROM paper_publication_types WHERE paper_id = %s", (paper_id,))
        assert {row["publication_type_id"] for row in cursor.fetchall()} == {"JA"}

        cursor.execute("SELECT journal_index_id FROM paper_journal_indices WHERE paper_id = %s", (paper_id,))
        assert {row["journal_index_id"] for row in cursor.fetchall()} == {"SSCI"}

        cursor.execute("SELECT education_level_id FROM paper_education_levels WHERE paper_id = %s", (paper_id,))
        assert {row["education_level_id"] for row in cursor.fetchall()} == {"HE"}

        cursor.execute("SELECT research_location_id FROM paper_research_locations WHERE paper_id = %s", (paper_id,))
        assert {row["research_location_id"] for row in cursor.fetchall()} == {"TW"}

        cursor.execute("SELECT research_focus_id FROM paper_research_focuses WHERE paper_id = %s", (paper_id,))
        assert {row["research_focus_id"] for row in cursor.fetchall()} == {"TO"}


def test_metadata_update(app_modules, excel_fixture_path, db_conn, tmp_path):
    load_data = app_modules["data_loader"].load_data
    load_data(str(excel_fixture_path))

    rows = [
        {
            "Code": "T001",
            "Unnamed: 1": "Test Author",
            "Unnamed: 2": 2020,
            "Unnamed: 3": "EMI Policy in Higher Education",
            "Unnamed: 4": "Test Journal",
            "Unnamed: 5": "10.1000/test001",
            "Unnamed: 6": "https://example.com",
            "Unnamed: 7": "Test Citation",
            "Unnamed: 8": "Policy discussion in higher education.",
            "JA": "1",
            "SCOPUS": "1",
            "HE": "1",
            "TW": "1",
            "TO": "1",
        }
    ]
    columns = [
        "Code", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6", "Unnamed: 7", "Unnamed: 8",
        "BC", "B", "JA",
        "SSCI", "AHCI", "ESCI", "LLBA", "SCOPUS", "THSS",
        "RE", "PD", "SQ", "IN", "CO", "TS", "CS",
        "HE", "KS",
        "TW", "CN", "HK", "AS", "EU", "OTH", "AR",
        "TO", "SO", "EP", "EL", "CL", "TT", "CD", "TM", "RL", "SI", "RM",
    ]

    df = pd.DataFrame(rows, columns=columns)
    updated_path = tmp_path / "metadata_update.xlsx"
    with pd.ExcelWriter(updated_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False, startrow=4)
        ws = writer.sheets["Sheet1"]
        for i in range(1, 5):
            ws.cell(row=i, column=1, value="NOTE")

    load_data(str(updated_path))

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM papers WHERE article_code = %s", ("T001",))
        paper_id = cursor.fetchone()["id"]

        cursor.execute("SELECT journal_index_id FROM paper_journal_indices WHERE paper_id = %s", (paper_id,))
        values = {row["journal_index_id"] for row in cursor.fetchall()}
        assert values == {"SCOPUS"}


def test_actual_codebook_format_import(app_modules, db_conn, tmp_path):
    load_data = app_modules["data_loader"].load_data

    columns = [
        "Paper ID", "Full APA Citation", "Journal Quality", "Research Paper Abstract",
        "EMI", "CLIL", "TE1", "TE2", "OP3", "EM1", "RS7", "ED4",
    ]
    rows = [
        {
            "Paper ID": "Abdeljaoued 2023",
            "Full APA Citation": (
                "Abdeljaoued, M. (2023). English-medium instruction in Tunisia: "
                "Perspectives of students. Frontiers in Psychology, 14, Article 1112255. "
                "https://doi.org/10.3389/fpsyg.2023.1112255"
            ),
            "Journal Quality": "SSCI Q1 -- Psychology (Multidisciplinary)",
            "Research Paper Abstract": "This article gives a Tunisian perspective to EMI.",
            "EMI": 1,
            "CLIL": 0,
            "TE1": 0,
            "TE2": 1,
            "OP3": 1,
            "EM1": 1,
            "RS7": 1,
            "ED4": 1,
        }
    ]

    path = tmp_path / "actual_codebook.xlsx"
    df = pd.DataFrame(rows, columns=columns)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False, startrow=1)
        ws = writer.sheets["Sheet1"]
        ws.cell(row=1, column=5, value="EMI or CLIL?")
        ws.cell(row=1, column=7, value="Research Topics")
        ws.cell(row=1, column=9, value="Research Results")
        ws.cell(row=1, column=10, value="Research Methods")
        ws.cell(row=1, column=11, value="Research Setting")
        ws.cell(row=1, column=12, value="Participants")

    result = load_data(str(path))

    assert result["ok"] is True
    assert result["inserted"] == 1
    assert result["skipped"] == 0
    assert result["errors"] == []

    with db_conn.cursor() as cursor:
        cursor.execute("SELECT id, title, year, doi, url FROM papers WHERE article_code = %s", ("Abdeljaoued 2023",))
        paper = cursor.fetchone()
        assert paper["title"] == "English-medium instruction in Tunisia: Perspectives of students"
        assert paper["year"] == 2023
        assert paper["doi"] == "10.3389/fpsyg.2023.1112255"
        assert paper["url"] == "https://doi.org/10.3389/fpsyg.2023.1112255"

        paper_id = paper["id"]
        cursor.execute("SELECT publication_type_id FROM paper_publication_types WHERE paper_id = %s", (paper_id,))
        assert {row["publication_type_id"] for row in cursor.fetchall()} == {"EMI"}
        cursor.execute("SELECT journal_index_id FROM paper_journal_indices WHERE paper_id = %s", (paper_id,))
        assert {row["journal_index_id"] for row in cursor.fetchall()} == {"TE2"}
        cursor.execute("SELECT study_nature_id FROM paper_study_natures WHERE paper_id = %s", (paper_id,))
        assert {row["study_nature_id"] for row in cursor.fetchall()} == {"OP3"}
        cursor.execute("SELECT research_focus_id FROM paper_research_focuses WHERE paper_id = %s", (paper_id,))
        assert {row["research_focus_id"] for row in cursor.fetchall()} == {"EM1"}
        cursor.execute("SELECT research_location_id FROM paper_research_locations WHERE paper_id = %s", (paper_id,))
        assert {row["research_location_id"] for row in cursor.fetchall()} == {"RS7"}
        cursor.execute("SELECT education_level_id FROM paper_education_levels WHERE paper_id = %s", (paper_id,))
        assert {row["education_level_id"] for row in cursor.fetchall()} == {"ED4"}
