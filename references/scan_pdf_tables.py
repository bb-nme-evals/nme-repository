from pathlib import Path
import pdfplumber

pdf = Path(r"c:\Users\bglen\Research\NMEs\references\1-s2.0-S0370269324004544-main.pdf")
markers = ["76Ge", "82Se", "100Mo", "130Te", "136Xe", "NME", "Table", "M_F", "M_GT", "M_T"]

with pdfplumber.open(str(pdf)) as p:
    print(f"pages={len(p.pages)}")
    for i, page in enumerate(p.pages, start=1):
        settings_line = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "text_tolerance": 3,
        }
        tables = page.extract_tables(table_settings=settings_line) or []

        if not tables:
            settings_text = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 5,
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 2,
                "min_words_horizontal": 1,
                "text_tolerance": 3,
                "text_x_tolerance": 2,
                "text_y_tolerance": 2,
            }
            tables = page.extract_tables(table_settings=settings_text) or []

        if not tables:
            continue

        hit = False
        previews = []
        for t in tables:
            rows = t or []
            flat = " ".join((c or "") for r in rows[:6] for c in (r or []))
            previews.append(flat[:260].replace("\n", " "))
            if any(m in flat for m in markers):
                hit = True

        if hit:
            print(f"PAGE {i}: tables={len(tables)}")
            for idx, pv in enumerate(previews, start=1):
                print(f"  table{idx}: {pv}")
