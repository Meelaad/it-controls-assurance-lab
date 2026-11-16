import csv
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT = "reports/workpaper.xlsx"

# sheet name, source csv, column widths (anything not listed gets 14)
SHEETS = [
    ("Controls", "control_matrix.csv", {"control": 28, "risk": 40, "owner": 24, "evidence": 40}),
    ("Testing", "test_results.csv", {"walkthrough": 60, "design_test": 40, "design_result": 50,
                                     "toe_test": 50, "exceptions": 60}),
    ("Findings", "findings.csv", {"title": 36, "condition": 50, "root_cause": 45, "risk": 40,
                                  "recommendation": 60, "owner": 24}),
    ("Retest", "retest.csv", {"what_was_done": 60, "retest_result": 60, "status": 30}),
    ("Change samples", "evidence/change_samples.csv", {"message": 60}),
]

HEADER = PatternFill("solid", fgColor="1F3864")
RESULT_FILL = {
    "Effective": PatternFill("solid", fgColor="C6EFCE"),
    "Ineffective": PatternFill("solid", fgColor="FFC7CE"),
    "Not tested": PatternFill("solid", fgColor="FFEB9C"),
    "High": PatternFill("solid", fgColor="FFC7CE"),
    "Medium": PatternFill("solid", fgColor="FFEB9C"),
    "Low": PatternFill("solid", fgColor="DDEBF7"),
}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def add_sheet(wb, name, path, widths):
    rows = read_csv(path)
    ws = wb.create_sheet(name)
    for r in rows:
        ws.append(r)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER
    for i, col in enumerate(rows[0], start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(col, 14)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if cell.value in RESULT_FILL:
                cell.fill = RESULT_FILL[cell.value]
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


def summary(wb):
    tests = list(csv.DictReader(open("test_results.csv", newline="", encoding="utf-8")))
    findings = list(csv.DictReader(open("findings.csv", newline="", encoding="utf-8")))
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Northwind Q4 2026 IRM control assessment"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append(["Period tested", "2026-08-01 to 2026-11-15"])
    ws.append(["Testing done", "2026-11-17"])
    ws.append([])
    ws.append(["Result", "Design", "Operating"])
    for result in ("Effective", "Ineffective", "Not tested"):
        ws.append([result,
                   sum(t["design"] == result for t in tests),
                   sum(t["operating"] == result for t in tests)])
    ws.append([])
    ws.append(["Findings by severity", "Count"])
    for sev in ("High", "Medium", "Low"):
        ws.append([sev, sum(f["severity"] == sev for f in findings)])
    for row in (5, 10):
        for cell in ws[row]:
            cell.font = Font(bold=True)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 14


def main():
    wb = Workbook()
    summary(wb)
    for name, path, widths in SHEETS:
        add_sheet(wb, name, path, widths)
    os.makedirs("reports", exist_ok=True)
    wb.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
