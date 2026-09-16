import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tabular_change_guard import InputError, check
from tabular_change_guard.cli import main


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.before = Path(self.temp.name) / "before.csv"
        self.after = Path(self.temp.name) / "after.csv"

    def pair(self, before, after, **options):
        self.before.write_text(before, encoding="utf-8", newline="")
        self.after.write_text(after, encoding="utf-8", newline="")
        return check(self.before, self.after, keys=["id"], **options)

    def test_allowed_change_and_reorder(self):
        r = self.pair("id,name,qty\n001, West ,0.10\n002,East,0.20\n",
                      "qty,name,id\n0.20,East,002\n0.10,West,001\n", allow=["name"], sums=["qty"])
        self.assertTrue(r["ok"])

    def test_protected_values_remain_exact(self):
        r = self.pair("id,v\n001,0.10\n", "id,v\n001,0.1\n")
        self.assertEqual(r["counts"], {"protected_value_changed": 1})

    def test_leading_zero_id_is_a_different_key(self):
        r = self.pair("id,v\n001,a\n", "id,v\n1,a\n")
        self.assertEqual(r["counts"], {"row_added": 1, "row_removed": 1})

    def test_missing_and_added_rows(self):
        r = self.pair("id,v\n1,a\n2,b\n", "id,v\n1,a\n3,c\n")
        self.assertEqual(r["issue_count"], 2)

    def test_changed_schema_blocks_comparison(self):
        r = self.pair("id,v\n1,a\n", "id,w\n1,a\n")
        self.assertFalse(r["comparison_performed"])
        self.assertEqual(r["counts"], {"column_added": 1, "column_removed": 1})

    def test_duplicate_keys_rejected_in_either_input(self):
        for b, a in [("id\n1\n1\n", "id\n1\n"), ("id\n1\n", "id\n1\n1\n")]:
            with self.subTest(before=b), self.assertRaises(InputError):
                self.pair(b, a)

    def test_blank_keys_rejected(self):
        with self.assertRaises(InputError):
            self.pair("id,v\n ,a\n", "id,v\n ,a\n")

    def test_composite_key(self):
        self.before.write_text("id,part,v\n1,a,x\n1,b,y\n", encoding="utf-8")
        self.after.write_text("id,part,v\n1,b,y\n1,a,x\n", encoding="utf-8")
        self.assertTrue(check(self.before, self.after, keys=["id", "part"])["ok"])

    def test_required_output(self):
        r = self.pair("id,v\n1,a\n", "id,v\n1, \n", allow=["v"], required=["v"])
        self.assertEqual(r["counts"], {"required_value_missing": 1})

    def test_decimal_rejects_nonfinite_exponents_and_whitespace(self):
        for value in ["NaN", "Infinity", "1e2", " 1", "", "１", "1_000"]:
            with self.subTest(value=value):
                r = self.pair("id,v\n1,1\n", "id,v\n1," + value + "\n", allow=["v"], decimals=["v"])
                self.assertEqual(r["counts"].get("invalid_decimal"), 1)

    def test_exact_decimal_sum(self):
        r = self.pair("id,v\n1,0.1\n2,0.2\n", "id,v\n1,0.3\n2,0\n", allow=["v"], sums=["v"])
        self.assertTrue(r["ok"])

    def test_long_decimal_total_detects_single_unit_change(self):
        value = "123456789012345678901234567890.00000000000000000001"
        altered = "123456789012345678901234567890.00000000000000000002"
        r = self.pair("id,v\n1," + value + "\n", "id,v\n1," + altered + "\n", allow=["v"], sums=["v"])
        self.assertEqual(r["counts"], {"total_changed": 1})

    def test_invalid_baseline_total_is_not_silently_ignored(self):
        r = self.pair("id,v\n1,\n", "id,v\n1,0\n", allow=["v"], sums=["v"])
        self.assertEqual(r["counts"], {"invalid_baseline_decimal": 1})

    def test_formula_like_text_on_any_output_column(self):
        for value in ["=1+1", "  @SUM(A1)", "+cmd", "-cmd", "\t=1"]:
            with self.subTest(value=value):
                r = self.pair("id,v\n1,a\n", "id,v\n1," + value + "\n", allow=["v"])
                self.assertEqual(r["counts"], {"formula_like_value": 1})

    def test_signed_numbers_not_flagged_as_formulas(self):
        for value in ["-42.50", "+3", "-.1"]:
            with self.subTest(value=value):
                self.assertTrue(self.pair("id,v\n1,a\n", "id,v\n1," + value + "\n", allow=["v"])["ok"])

    def test_formula_check_explicit_opt_out(self):
        self.assertTrue(self.pair("id,v\n1,a\n", "id,v\n1,=1\n", allow=["v"], check_formulas=False)["ok"])

    def test_quoted_newlines_and_commas(self):
        r = self.pair('id,v\n1,"hello,\nworld"\n', 'id,v\n1,"hello,\nworld"\n')
        self.assertTrue(r["ok"])
        self.assertEqual(r["before"]["records"], 1)

    def test_malformed_csv(self):
        for value in ['id,v\n1,"unterminated', 'id,v\n1,a,b\n', 'id,v\n1\n', 'id,v\n\n']:
            with self.subTest(value=value), self.assertRaises(InputError):
                self.pair(value, value)

    def test_invalid_headers(self):
        for value in ["", "id,id\n1,1\n", "id,\n1,a\n", "id, \n1,a\n"]:
            with self.subTest(value=value), self.assertRaises(InputError):
                self.pair(value, value)

    def test_header_only_is_valid(self):
        self.assertTrue(self.pair("id,v\n", "id,v\n", sums=["v"])["ok"])

    def test_bom_and_cp932(self):
        self.before.write_bytes("id,部署\n001,製造\n".encode("cp932"))
        self.after.write_bytes("id,部署\n001,製造\n".encode("utf-8-sig"))
        self.assertTrue(check(self.before, self.after, keys=["id"], before_encoding="cp932")["ok"])

    def test_tsv(self):
        self.assertTrue(self.pair("id\tv\n1\ta\n", "id\tv\n1\ta\n", delimiter="\t")["ok"])

    def test_report_omits_cell_values_and_paths(self):
        r = self.pair("id,v\nprivate-id,private-before\n", "id,v\nprivate-id,private-after\n")
        payload = json.dumps(r)
        self.assertNotIn("private", payload)
        self.assertNotIn(str(self.before), payload)
        self.assertEqual(r["issues"][0]["before_record"], 1)

    def test_issue_cap_keeps_complete_counts(self):
        r = self.pair("id,v\n1,a\n2,b\n3,c\n", "id,v\n1,x\n2,y\n3,z\n", max_issues=1)
        self.assertEqual(r["issue_count"], 3)
        self.assertEqual(len(r["issues"]), 1)
        self.assertTrue(r["issues_truncated"])

    def test_hashes_and_inputs_untouched(self):
        b, a = "id,v\n1,a\n", "id,v\n1,b\n"
        r = self.pair(b, a)
        self.assertEqual(self.before.read_bytes(), b.encode())
        self.assertEqual(self.after.read_bytes(), a.encode())
        self.assertEqual(r["before"]["sha256"], hashlib.sha256(b.encode()).hexdigest())

    def test_byte_limit(self):
        with self.assertRaises(InputError):
            self.pair("id\n1\n", "id\n1\n", max_bytes=2)

    def test_configuration_errors(self):
        self.pair("id,v\n1,a\n", "id,v\n1,a\n")
        for options in [{"keys": []}, {"keys": "id"}, {"allow": ["id"]},
                        {"allow": ["missing"]}, {"keys": ["id", "id"]},
                        {"delimiter": "xx"}, {"delimiter": '"'}, {"max_issues": 0}]:
            with self.subTest(options=options), self.assertRaises(InputError):
                check(self.before, self.after, **({"keys": ["id"]} | options))

    def test_read_errors_do_not_echo_paths(self):
        for encoding in ["not-an-encoding", "utf-8"]:
            with self.subTest(encoding=encoding), self.assertRaises(InputError) as caught:
                check(self.before, self.after, keys=["id"], before_encoding=encoding)
            self.assertNotIn(str(self.before), str(caught.exception))

    def test_bad_encoding(self):
        self.before.write_bytes(b"id,v\n1,\xff\n")
        self.after.write_bytes(b"id,v\n1,a\n")
        with self.assertRaises(InputError):
            check(self.before, self.after, keys=["id"])

    def test_cli_exit_codes(self):
        for after, expected in [("id,v\n1,a\n", 0), ("id,v\n1,b\n", 1), ("id,id\n1,1\n", 2)]:
            self.before.write_text("id,v\n1,a\n", encoding="utf-8")
            self.after.write_text(after, encoding="utf-8")
            with self.subTest(expected=expected):
                run = subprocess.run([sys.executable, "-m", "tabular_change_guard", str(self.before), str(self.after), "--key", "id"], capture_output=True, text=True)
                self.assertEqual(run.returncode, expected, run.stderr)
                payload = json.loads(run.stderr if expected == 2 else run.stdout)
                self.assertEqual(payload.get("ok"), None if expected == 2 else expected == 0)

    def test_cli_tsv_text(self):
        self.pair("id\tv\n1\ta\n", "id\tv\n1\ta\n", delimiter="\t")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(self.before), str(self.after), "--key", "id", "--delimiter", "tab", "--format", "text"])
        self.assertEqual(code, 0)
        self.assertTrue(output.getvalue().startswith("PASS"))


if __name__ == "__main__":
    unittest.main()
