"""
Generate a Tableau packaged workbook (tableau/AI_Usage_Analytics.twbx) from the gold CSVs.

The .twbx bundles the workbook XML and the CSV files, so it opens anywhere in
Tableau Desktop or Tableau Public without re-pointing data sources.

    python scripts/export_for_tableau.py      # refresh tableau/data/*.csv first
    python scripts/build_tableau_workbook.py
"""

from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tableau" / "data"
OUT_TWBX = ROOT / "tableau" / "AI_Usage_Analytics.twbx"
TWB_NAME = "AI_Usage_Analytics.twb"
PACKAGED_DIR = "Data/data"  # where the CSVs live inside the .twbx

# Data sources: key -> (csv file, caption)
SOURCES = {
    "fct": ("fct_ai_usage.csv", "Users (fact)"),
    "tool": ("mart_tool_performance.csv", "Tool Performance"),
    "purpose": ("mart_purpose_impact.csv", "Purpose Impact"),
    "plan": ("mart_plan_tier_value.csv", "Plan Tier Value"),
    "country": ("mart_country_summary.csv", "Country Summary"),
    "segment": ("mart_segment_summary.csv", "Segment Summary"),
    "corr": ("mart_metric_correlations.csv", "Metric Correlations"),
    "dq": ("mart_data_quality.csv", "Data Quality"),
}
# Numeric columns that are really categories / sort keys
FORCE_DIMENSION = {"usage_band_order", "popularity_rank", "satisfaction_rank"}
AGG_DERIVATION = {"none": "None", "sum": "Sum", "avg": "Avg", "min": "Min"}

# Tableau's standard card layout for a worksheet window
WORKSHEET_CARDS = (
    "<cards>"
    "<edge name='left'><strip size='160'>"
    "<card type='pages' /><card type='filters' /><card type='marks' />"
    "</strip></edge>"
    "<edge name='top'>"
    "<strip size='2147483647'><card type='columns' /></strip>"
    "<strip size='2147483647'><card type='rows' /></strip>"
    "<strip size='31'><card type='title' /></strip>"
    "</edge>"
    "</cards>"
)


# --------------------------------------------------------------------------- #
# Column metadata
# --------------------------------------------------------------------------- #
def infer_types(path: Path) -> dict[str, str]:
    """Tableau datatype per CSV column: integer, real or string."""
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        types = dict.fromkeys(reader.fieldnames, "integer")
        for row in reader:
            for col, value in row.items():
                if not value or types[col] == "string":
                    continue
                try:
                    int(value)
                except ValueError:
                    try:
                        float(value)
                        types[col] = "real"
                    except ValueError:
                        types[col] = "string"
    return types


TYPES = {key: infer_types(DATA / fname) for key, (fname, _) in SOURCES.items()}


def caption(name: str) -> str:
    fixes = {"ai": "AI", "avg": "Avg", "pct": "%", "hrs": "hrs", "id": "ID"}
    return " ".join(fixes.get(w, w.capitalize()) for w in name.split("_"))


def ds_name(key: str) -> str:
    return f"federated.{key}"


def col_meta(key: str, col: str) -> tuple[str, str, str]:
    """(datatype, role, type) for a column."""
    datatype = TYPES[key][col]
    if datatype == "string":
        return datatype, "dimension", "nominal"
    if col in FORCE_DIMENSION:
        return datatype, "dimension", "ordinal"
    return datatype, "measure", "quantitative"


def column_xml(key: str, col: str, indent: str, with_caption: bool = False) -> str:
    datatype, role, typ = col_meta(key, col)
    cap = f"caption={quoteattr(caption(col))} " if with_caption else ""
    return f"{indent}<column {cap}datatype='{datatype}' name='[{col}]' role='{role}' type='{typ}' />"


# --------------------------------------------------------------------------- #
# Fields placed on shelves
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Field:
    key: str
    col: str
    agg: str = "none"  # none | sum | avg | min

    @property
    def is_dim(self) -> bool:
        return self.agg == "none"

    @property
    def instance(self) -> str:
        if not self.is_dim:
            suffix = "qk"
        else:
            suffix = "nk" if col_meta(self.key, self.col)[2] == "nominal" else "ok"
        return f"[{self.agg}:{self.col}:{suffix}]"

    @property
    def ref(self) -> str:
        return f"[{ds_name(self.key)}].{self.instance}"

    def instance_xml(self) -> str:
        typ = col_meta(self.key, self.col)[2] if self.is_dim else "quantitative"
        return (
            f"            <column-instance column='[{self.col}]' derivation='{AGG_DERIVATION[self.agg]}' "
            f"name='{self.instance}' pivot='key' type='{typ}' />"
        )


def member_xml(field: Field, value: str, extra: str = "") -> str:
    member = quoteattr(f'"{value}"')
    return f"<groupfilter function='member' level='{field.instance}' member={member}{extra} />"


def exclude_filter(field: Field, values: list[str]) -> str:
    members = "".join(member_xml(field, v) for v in values)
    if len(values) > 1:
        members = f"<groupfilter function='union'>{members}</groupfilter>"
    return (
        "<groupfilter function='except' user:ui-domain='database' "
        "user:ui-enumeration='exclusive' user:ui-marker='enumerate'>"
        f"<groupfilter function='level-members' level='{field.instance}' />{members}</groupfilter>"
    )


def keep_filter(field: Field, values: list[str]) -> str:
    ui = " user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate'"
    if len(values) == 1:
        return member_xml(field, values[0], ui)
    members = "".join(member_xml(field, v) for v in values)
    return f"<groupfilter function='union'{ui}>{members}</groupfilter>"


# --------------------------------------------------------------------------- #
# Worksheets
# --------------------------------------------------------------------------- #
def worksheet_xml(
    name, key, rows, cols, mark, title, color=None, size=None, text=None,
    detail=None, exclude=None, keep=None, sort=None, diverging=False, labels=False,
):
    """
    rows/cols : list[Field] (nested left-to-right)
    exclude   : (Field, [values]) values to filter out
    keep      : (Field, [values]) values to keep
    sort      : (dimension Field, measure Field, 'ASC'|'DESC')
    """
    fields = [*rows, *cols, *(f for f in (color, size, text, detail) if f)]
    fields += [spec[0] for spec in (exclude, keep) if spec]
    if sort:
        fields += [sort[0], sort[1]]
    unique = list(dict.fromkeys(fields))  # keep order, drop duplicates
    base_cols = list(dict.fromkeys(f.col for f in unique))

    deps = "\n".join(
        [column_xml(key, c, "            ") for c in base_cols]
        + [f.instance_xml() for f in sorted(set(unique), key=lambda f: f.instance)]
    )

    filters, slices = [], []
    for spec, builder in ((exclude, exclude_filter), (keep, keep_filter)):
        if spec:
            field, values = spec
            filters.append(
                f"          <filter class='categorical' column='{field.ref}'>\n"
                f"            {builder(field, values)}\n"
                "          </filter>"
            )
            slices.append(f"            <column>{field.ref}</column>")
    slices_xml = "          <slices>\n" + "\n".join(slices) + "\n          </slices>" if slices else ""
    sort_xml = ""
    if sort:
        dim, measure, direction = sort
        sort_xml = (
            f"          <sort class='computed' column='{dim.ref}' direction='{direction}' "
            f"using='{measure.ref}' />"
        )

    encodings = "".join(
        f"<{tag} column='{f.ref}' />"
        for tag, f in (("color", color), ("size", size), ("lod", detail), ("text", text))
        if f
    )
    enc_xml = f"            <encodings>{encodings}</encodings>" if encodings else ""
    pane_style = (
        "            <style><style-rule element='mark'>"
        "<format attr='mark-labels-show' value='true' /></style-rule></style>"
        if labels else ""
    )
    table_style = ""
    if diverging and color:
        table_style = (
            f"<style-rule element='mark'><encoding attr='color' field='{color.ref}' "
            "palette='red_blue_diverging_10_0' type='interpolated'>"
            "<range-reversed>false</range-reversed></encoding></style-rule>"
        )

    def shelf(fs: list[Field]) -> str:
        joined = " / ".join(f.ref for f in fs)
        return f"({joined})" if len(fs) > 1 else joined

    body = "\n".join(
        part for part in (
            "        <view>",
            "          <datasources>",
            f"            <datasource caption={quoteattr(SOURCES[key][1])} name='{ds_name(key)}' />",
            "          </datasources>",
            f"          <datasource-dependencies datasource='{ds_name(key)}'>",
            deps,
            "          </datasource-dependencies>",
            *filters,
            slices_xml,
            sort_xml,
            "          <aggregation value='true' />",
            "        </view>",
            f"        <style>{table_style}</style>",
            "        <panes>",
            "          <pane selection-relaxation-option='selection-relaxation-allow'>",
            "            <view><breakdown value='auto' /></view>",
            f"            <mark class='{mark}' />",
            enc_xml,
            pane_style,
            "          </pane>",
            "        </panes>",
            f"        <rows>{shelf(rows)}</rows>",
            f"        <cols>{shelf(cols)}</cols>",
        ) if part
    )
    return (
        f"    <worksheet name={quoteattr(name)}>\n"
        "      <layout-options>\n"
        f"        <title><formatted-text><run fontsize='13' bold='true'>{escape(title)}</run>"
        "</formatted-text></title>\n"
        "      </layout-options>\n"
        "      <table>\n"
        f"{body}\n"
        "      </table>\n"
        "    </worksheet>"
    )


F = Field
SHEETS = [
    dict(name="Tool Popularity", key="tool", mark="Bar",
         title="Q1 · Which AI tools are used most? (colour = net recommend score)",
         rows=[F("tool", "ai_tool")], cols=[F("tool", "users", "sum")],
         color=F("tool", "net_recommend_score", "avg"), labels=True,
         exclude=(F("tool", "ai_tool"), ["Unknown"]),
         sort=(F("tool", "ai_tool"), F("tool", "users", "sum"), "DESC")),
    dict(name="Tool Quality", key="tool", mark="Circle",
         title="Q2 · Productivity vs satisfaction by tool (size = users)",
         rows=[F("tool", "avg_satisfaction", "avg")], cols=[F("tool", "avg_productivity", "avg")],
         size=F("tool", "users", "sum"), color=F("tool", "net_recommend_score", "avg"),
         text=F("tool", "ai_tool"), labels=True,
         exclude=(F("tool", "ai_tool"), ["Unknown"])),
    dict(name="Usage Intensity", key="fct", mark="Line",
         title="Q4 · More daily AI use → more hours saved per week",
         rows=[F("fct", "time_saved_hours_per_week", "avg")], cols=[F("fct", "usage_band")],
         color=F("fct", "user_type"), labels=True,
         exclude=(F("fct", "usage_band"), ["Unknown"]),
         sort=(F("fct", "usage_band"), F("fct", "usage_band_order", "min"), "ASC")),
    dict(name="Productivity by Usage", key="fct", mark="Bar",
         title="Q4 · Average productivity score by daily AI usage",
         rows=[F("fct", "productivity_score", "avg")], cols=[F("fct", "usage_band")],
         color=F("fct", "productivity_score", "avg"), labels=True,
         exclude=(F("fct", "usage_band"), ["Unknown"]),
         sort=(F("fct", "usage_band"), F("fct", "usage_band_order", "min"), "ASC")),
    dict(name="Purpose Impact", key="purpose", mark="Bar",
         title="Q3 · Hours saved per week by AI purpose",
         rows=[F("purpose", "ai_purpose"), F("purpose", "user_type")],
         cols=[F("purpose", "avg_time_saved_hrs_week", "avg")],
         color=F("purpose", "user_type"), labels=True,
         exclude=(F("purpose", "ai_purpose"), ["Unknown"]),
         sort=(F("purpose", "ai_purpose"), F("purpose", "avg_time_saved_hrs_week", "avg"), "DESC")),
    dict(name="Free vs Paid", key="plan", mark="Bar",
         title="Q5 · Net recommend score by plan tier",
         rows=[F("plan", "plan_tier"), F("plan", "user_type")],
         cols=[F("plan", "net_recommend_score", "avg")],
         color=F("plan", "user_type"), labels=True,
         exclude=(F("plan", "plan_tier"), ["Unknown"])),
    dict(name="Countries", key="country", mark="Bar",
         title="Q6 · Users by country (colour = avg productivity)",
         rows=[F("country", "country")], cols=[F("country", "users", "sum")],
         color=F("country", "avg_productivity", "avg"), labels=True,
         exclude=(F("country", "country"), ["Unknown"]),
         sort=(F("country", "country"), F("country", "users", "sum"), "DESC")),
    dict(name="Job Families", key="segment", mark="Square",
         title="Q7 · Hours saved per week by job family",
         rows=[F("segment", "segment_value")], cols=[F("segment", "user_type")],
         color=F("segment", "avg_time_saved_hrs_week", "avg"),
         text=F("segment", "avg_time_saved_hrs_week", "avg"), labels=True,
         keep=(F("segment", "segment_type"), ["profession_category"])),
    dict(name="Correlations", key="corr", mark="Square",
         title="Q8 · Correlation between metrics (Pearson r)",
         rows=[F("corr", "metric_y")], cols=[F("corr", "metric_x")],
         color=F("corr", "pearson_r", "avg"), text=F("corr", "pearson_r", "avg"),
         diverging=True, labels=True),
    dict(name="Data Quality", key="dq", mark="Bar",
         title="Q9 · What the pipeline fixed in the raw data",
         rows=[F("dq", "check_name")], cols=[F("dq", "affected_rows", "sum")],
         color=F("dq", "check_type"), labels=True,
         sort=(F("dq", "check_name"), F("dq", "affected_rows", "sum"), "DESC")),
]

# Dashboards: sheets are laid out in a 2-column grid
DASHBOARDS = [
    ("Executive Overview", ["Tool Popularity", "Usage Intensity", "Countries", "Tool Quality"]),
    ("Value Deep Dive", ["Purpose Impact", "Free vs Paid", "Job Families", "Productivity by Usage"]),
    ("Behind the Data", ["Correlations", "Data Quality"]),
]


# --------------------------------------------------------------------------- #
# Data sources, dashboards, windows
# --------------------------------------------------------------------------- #
def datasource_xml(key: str) -> str:
    fname, cap = SOURCES[key]
    table = fname.replace(".csv", "#csv")
    rel_cols = "\n".join(
        f"            <column datatype='{t}' name={quoteattr(c)} ordinal='{i}' />"
        for i, (c, t) in enumerate(TYPES[key].items())
    )
    meta_cols = "\n".join(column_xml(key, c, "      ", with_caption=True) for c in TYPES[key])
    return f"""    <datasource caption={quoteattr(cap)} inline='true' name='{ds_name(key)}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption={quoteattr(fname)} name='textscan.{key}'>
            <connection class='textscan' directory='{PACKAGED_DIR}' filename={quoteattr(fname)} \
password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.{key}' name={quoteattr(fname)} table='[{table}]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{rel_cols}
          </columns>
        </relation>
      </connection>
      <aliases enabled='yes' />
{meta_cols}
    </datasource>"""


def dashboard_xml(name: str, sheets: list[str]) -> str:
    """Title on top, sheets in a 2-column grid (a lone last sheet spans the full width)."""
    margin, full_w, title_h = 800, 98400, 7000
    top = margin + title_h
    avail_h = 100000 - top - margin
    zone_ids = iter(range(3, 100))
    zones = [f"<zone h='{title_h}' id='{next(zone_ids)}' type-v2='title' w='{full_w}' x='{margin}' y='{margin}' />"]

    n = len(sheets)
    two_up = n > 2
    rows_n = (n + 1) // 2 if two_up else n
    cell_w, cell_h = full_w // 2, avail_h // rows_n
    for i, sheet in enumerate(sheets):
        r, c = divmod(i, 2) if two_up else (i, 0)
        spans = not two_up or (n % 2 == 1 and i == n - 1)
        w = full_w if spans else cell_w
        zones.append(
            f"<zone h='{cell_h}' id='{next(zone_ids)}' name={quoteattr(sheet)} "
            f"w='{w}' x='{margin + c * cell_w}' y='{top + r * cell_h}' />"
        )
    zone_xml = "\n".join("          " + z for z in zones)
    return f"""    <dashboard name={quoteattr(name)}>
      <style />
      <size maxheight='900' maxwidth='1400' minheight='900' minwidth='1400' />
      <zones>
        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
{zone_xml}
        </zone>
      </zones>
    </dashboard>"""


def windows_xml() -> str:
    out = [
        f"    <window class='worksheet' name={quoteattr(s['name'])}>{WORKSHEET_CARDS}</window>"
        for s in SHEETS
    ]
    for i, (dash, _) in enumerate(DASHBOARDS):
        maximized = "maximized='true' " if i == 0 else ""
        out.append(f"    <window class='dashboard' {maximized}name={quoteattr(dash)} />")
    return "\n".join(out)


def used_sources() -> list[str]:
    keys = {s["key"] for s in SHEETS}
    return [k for k in SOURCES if k in keys]


def build() -> str:
    datasources = "\n".join(datasource_xml(k) for k in used_sources())
    worksheets = "\n".join(worksheet_xml(**s) for s in SHEETS)
    dashboards = "\n".join(dashboard_xml(n, s) for n, s in DASHBOARDS)
    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2023.3.0 (20233.23.1017.0948)' source-platform='mac' \
version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
{datasources}
  </datasources>
  <worksheets>
{worksheets}
  </worksheets>
  <dashboards>
{dashboards}
  </dashboards>
  <windows source-height='30'>
{windows_xml()}
  </windows>
</workbook>
"""


def main() -> None:
    twb = build()
    with zipfile.ZipFile(OUT_TWBX, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(TWB_NAME, twb)
        for key in used_sources():
            fname = SOURCES[key][0]
            z.write(DATA / fname, f"{PACKAGED_DIR}/{fname}")
    print(
        f"wrote {OUT_TWBX.relative_to(ROOT)}  "
        f"({len(SHEETS)} sheets, {len(DASHBOARDS)} dashboards, {len(used_sources())} data sources)"
    )


if __name__ == "__main__":
    main()
