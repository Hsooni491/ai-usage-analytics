"""Structural checks for the Databricks AI/BI dashboard definition."""

import json
import re
from collections import defaultdict
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboards" / "ai_usage_analytics.lvdash.json"
WIDGET_VERSIONS = {"counter": 2, "table": 2, "bar": 3, "line": 3, "heatmap": 3, "filter-multi-select": 2}


@pytest.fixture(scope="module")
def dash():
    return json.loads(DASHBOARD.read_text())


def widgets(dash):
    for page in dash["pages"]:
        for item in page["layout"]:
            yield page, item["widget"], item["position"]


def test_datasets_use_bare_table_names(dash):
    for ds in dash["datasets"]:
        sql = "".join(ds["queryLines"])
        for table in re.findall(r"\bFROM\s+([\w.`]+)", sql, flags=re.I):
            assert "." not in table, f"{ds['name']}: use a bare table name, got {table}"
        # queryLines are joined verbatim, so each must end with whitespace
        assert all(line.endswith((" ", "\n")) for line in ds["queryLines"]), ds["name"]


def test_pages_have_required_keys(dash):
    for page in dash["pages"]:
        assert page["pageType"] in {"PAGE_TYPE_CANVAS", "PAGE_TYPE_GLOBAL_FILTERS"}
        assert page["layoutVersion"] == "GRID_V1"


def test_widget_names_are_unique_and_safe(dash):
    names = [w["name"] for _, w, _ in widgets(dash)]
    assert len(names) == len(set(names))
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+", n) for n in names)


def test_field_bindings_and_versions(dash):
    datasets = {d["name"]: d for d in dash["datasets"]}
    for _, w, _ in widgets(dash):
        if "multilineTextboxSpec" in w:
            continue
        spec = w["spec"]
        assert spec["version"] == WIDGET_VERSIONS[spec["widgetType"]], w["name"]
        query = w["queries"][0]["query"]
        ds = datasets[query["datasetName"]]
        measures = {c["displayName"] for c in ds.get("columns", [])}
        field_names = {fld["name"] for fld in query["fields"]}
        for fld in query["fields"]:
            for measure in re.findall(r"MEASURE\(`([^`]+)`\)", fld["expression"]):
                assert measure in measures, f"{w['name']}: unknown measure {measure}"
        enc_text = json.dumps(spec["encodings"])
        for bound in re.findall(r'"fieldName": "([^"]+)"', enc_text):
            assert bound in field_names, f"{w['name']}: encoding field {bound} missing from query fields"


def test_canvas_rows_fill_twelve_columns(dash):
    for page in dash["pages"]:
        if page["pageType"] != "PAGE_TYPE_CANVAS":
            continue
        rows = defaultdict(int)
        for item in page["layout"]:
            pos = item["position"]
            rows[pos["y"]] += pos["width"]
            assert pos["x"] + pos["width"] <= 12
        assert all(width == 12 for width in rows.values()), f"{page['name']}: row widths {dict(rows)}"
