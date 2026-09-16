import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tabular_change_guard import InputError, check, load_contract
from tabular_change_guard.cli import main


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.contract = root / "private-contract.json"
        self.before, self.after = root / "before.csv", root / "after.csv"
        self.before.write_text("id,team,qty\n001, West ,0.1\n002,East,0.2\n", encoding="utf-8")
        self.after.write_text("id,team,qty\n002,East,0.2\n001,West,0.1\n", encoding="utf-8")
        self.rules = {"schema_version": 1, "keys": ["id"], "allow": ["team"], "sums": ["qty"]}

    def write(self, rules):
        self.contract.write_text(json.dumps(rules), encoding="utf-8")

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([str(self.before), str(self.after), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_api_matches_inline_rules(self):
        self.write(self.rules)
        self.assertEqual(check(self.before, self.after, **load_contract(self.contract)),
                         check(self.before, self.after, keys=["id"], allow=["team"], sums=["qty"]))

    def test_cli_pass_fail_and_inputs_untouched(self):
        self.write(self.rules)
        original = self.before.read_bytes()
        code, out, err = self.run_cli("--contract", str(self.contract))
        self.assertEqual(code, 0, err)
        self.assertTrue(json.loads(out)["ok"])
        self.after.write_text("id,team,qty\n1,West,0.1\n002,East,0.2\n", encoding="utf-8")
        code, out, err = self.run_cli("--contract", str(self.contract))
        self.assertEqual(code, 1, err)
        self.assertEqual(json.loads(out)["counts"], {"row_added": 1, "row_removed": 1})
        self.assertEqual(self.before.read_bytes(), original)

    def test_cli_does_not_allow_rule_overrides(self):
        self.write(self.rules)
        for args in [("--allow", "qty"), ("--allow-formulas",), ("--key", "id"),
                     ("--delimiter", ","), ("--before-encoding", "utf-8")]:
            with self.subTest(args=args):
                code, out, err = self.run_cli("--contract", str(self.contract), *args)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("cannot be combined", json.loads(err)["message"])

    def test_cli_requires_rules(self):
        self.assertEqual(self.run_cli()[0], 2)

    def test_invalid_schema_and_types(self):
        cases = [[], None, {}, {"keys": ["id"]}]
        for field, values in {"schema_version": [True, 1.0, 2, "1"],
                              "keys": [[], "id", None, [1], ["id", "id"]],
                              "allow": ["team", None], "check_formulas": ["false", 0, None],
                              "delimiter": [None, 3], "after_encoding": [None]}.items():
            cases.extend(dict(self.rules, **{field: value}) for value in values)
        cases.append(dict(self.rules, unknowingly_allow_all=True))
        for rules in cases:
            with self.subTest(rules=rules), self.assertRaises(InputError):
                self.write(rules)
                load_contract(self.contract)

    def test_duplicate_malformed_and_oversized_contracts(self):
        for raw in [b'{"schema_version":1,"keys":["id"],"keys":["other"]}',
                    b'{"private-secret":', b'\xff', b' ' * (64 * 1024 + 1),
                    b'[' * 2000 + b']' * 2000]:
            with self.subTest(length=len(raw)), self.assertRaises(InputError) as caught:
                self.contract.write_bytes(raw)
                load_contract(self.contract)
            self.assertNotIn("private", str(caught.exception))

    def test_missing_contract_is_private_cli_error(self):
        code, out, err = self.run_cli("--contract", str(self.contract))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotIn("private", err)
        self.assertEqual(json.loads(err)["error"], "invalid_input")

    def test_bom_tsv_and_formula_setting(self):
        self.before.write_bytes("id\t部署\n001\t製造\n".encode("cp932"))
        self.after.write_bytes("id\t部署\n001\t=1\n".encode("utf-8-sig"))
        rules = {"schema_version": 1, "keys": ["id"], "allow": ["部署"],
                 "before_encoding": "cp932", "delimiter": "\t", "check_formulas": False}
        self.contract.write_text(json.dumps(rules), encoding="utf-8-sig")
        code, out, err = self.run_cli("--contract", str(self.contract), "--format", "text")
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith("PASS"))

    def test_semantically_invalid_contract_is_not_success(self):
        for option in [{"allow": ["id"]}, {"sums": ["missing"]}, {"delimiter": "tab"},
                       {"after_encoding": "invalid-encoding"}]:
            self.write(dict(self.rules, **option))
            self.assertEqual(self.run_cli("--contract", str(self.contract))[0], 2)
