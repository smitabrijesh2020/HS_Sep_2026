"""Builds throwaway .xlsx fixtures for tests, shaped like real workbooks
found during development but containing only fabricated values.

Never hardcode real employee data here or in any caller - see
docs/security_privacy_checklist.md.
"""
from __future__ import annotations

from pathlib import Path

import openpyxl


def build_workbook(path: Path, sheets: dict[str, list[list]]) -> Path:
    """`sheets` maps sheet name -> list of rows (first row = headers)."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        ws = workbook.create_sheet(name)
        for row in rows:
            ws.append(row)
    workbook.save(path)
    return path


# Real header shapes found this session (values below are always fabricated).
NOMINATION_TRACKER_HEADERS = ["Emp ID", "Name", "Email", "Certification Name", "TRF No.", "Prerequisite Status"]
HS_REPORT_HEADERS = [
    "EMPLID", "EMP_NAME", "Email Id ", "Global Id", "Employee Status", "Gender",
    "Unified Grade", "Grade", "Supervisor Email", "Employee Location", "Data Source",
    "Certification Category Name", "Certificate_Name", "Certification Status",
    "Date_Of_Certification", "Certification Validity, If any", "Type_of_Entry",
    "Service Line", "Sub-BU name", "BU name", "SBU", "Adjusted SBU", "Alliance", "Year",
    "Certificate Unique Name", "Certificate Level", "Certificate Code", "Is HyperScaler",
    "Validity Years", "Certificate Validity Status",
]
IMOCHA_REPORT_HEADERS = [
    "Invited_By_Email", "Appeared_On", "Employee_ID", "Candidate_Name",
    "Candidate_Email_Address", "Competency", "Job_Role", "Candidate_Status", "Test_Id",
    "Test_Name", "Test_Status", "Test_Link_Name", "Test_Score", "Candidate_Score",
    "Percentage", "Performance_Category", "Total_Questions ", "Test_Duration(minutes)",
    "Time_Taken(minutes)", "Candidate_Feedback", "Proctoring_Flag", "Window_Violation",
    "Time_Violation", "Applicant_ID", "Percentile", "Completion_Time_Flag",
    "Avg_Test_Time(Minutes)", "PDF Report link", "Strengths", "Areas of Improvement",
    "Test Navigation Type",
]
