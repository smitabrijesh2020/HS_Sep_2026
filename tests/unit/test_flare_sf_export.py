import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from exports.flare_sf_export import DEFAULT_FLARE_MAPPING, build_export, validate_rows


class TestExportFramework(unittest.TestCase):
    def test_valid_row_maps_cleanly(self):
        rows = [{
            "employee_code": "SYN-001", "display_name": "Ava Example", "email": "ava@example.org",
            "program_name": "AWS SAA Readiness", "trf_number": "TRF1", "eligibility_status": "Eligible",
            "nomination_status": "Confirmed",
        }]
        result = build_export(rows, "FLARE", DEFAULT_FLARE_MAPPING)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.rows[0]["EmployeeID"], "SYN-001")

    def test_missing_required_field_is_flagged(self):
        rows = [{"employee_code": "", "display_name": "Ava", "email": "a@x.org",
                 "program_name": "P", "trf_number": "T1"}]
        errors = validate_rows(rows)
        self.assertTrue(any(e.field == "employee_code" for e in errors))

    def test_duplicate_rows_are_flagged(self):
        row = {"employee_code": "SYN-001", "display_name": "Ava", "email": "a@x.org",
               "program_name": "P", "trf_number": "T1"}
        errors = validate_rows([row, dict(row)])
        self.assertTrue(any("Duplicate" in e.message for e in errors))


if __name__ == "__main__":
    unittest.main()
