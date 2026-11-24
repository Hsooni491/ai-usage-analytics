"""The generated Tableau workbook must be well-formed and internally consistent."""

import importlib.util
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts" / "build_tableau_workbook.py")
builder = importlib.util.module_from_spec(spec)
sys.modules["builder"] = builder  # dataclasses need the module registered
spec.loader.exec_module(builder)


def test_workbook_references_are_consistent():
    root = ET.fromstring(builder.build())
    ds_cols = {d.get("name"): {c.get("name") for c in d.findall("column")} for d in root.find("datasources")}
    sheets = {w.get("name") for w in root.iter("worksheet")}
    assert len(sheets) == len(builder.SHEETS)

    for ws in root.iter("worksheet"):
        dep = ws.find(".//datasource-dependencies")
        declared = {c.get("name") for c in dep.findall("column-instance")}
        assert {c.get("name") for c in dep.findall("column")} <= ds_cols[dep.get("datasource")]
        used = set(re.findall(r"\[federated\.\w+\]\.(\[[^\]]+\])", ET.tostring(ws, encoding="unicode")))
        assert used <= declared, f"{ws.get('name')} uses undeclared fields {used - declared}"

    for dash in root.iter("dashboard"):
        for zone in dash.iter("zone"):
            assert zone.get("name") is None or zone.get("name") in sheets
