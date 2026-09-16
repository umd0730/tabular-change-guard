"""The caller's decimal settings must not change an exact CSV comparison."""

import tempfile
import unittest
from decimal import Inexact, ROUND_DOWN, localcontext
from pathlib import Path

from tabular_change_guard import check


class DecimalContextTests(unittest.TestCase):
    def compare(self, before_values, after_values, trapped):
        with tempfile.TemporaryDirectory() as directory:
            before = Path(directory) / "before.csv"
            after = Path(directory) / "after.csv"
            for path, values in ((before, before_values), (after, after_values)):
                path.write_text("id,v\n" + "".join(
                    f"{index},{value}\n" for index, value in enumerate(values, 1)
                ), encoding="utf-8")
            with localcontext() as context:
                context.prec = 2
                context.Emax = 3
                context.Emin = -3
                context.clamp = 1
                context.rounding = ROUND_DOWN
                for signal in context.traps:
                    context.traps[signal] = trapped
                context.flags[Inexact] = True
                original = repr(context)
                result = check(before, after, keys=["id"], allow=["v"], sums=["v"])
                self.assertEqual(repr(context), original)
                return result

    def test_different_large_totals_never_compare_as_equal_infinities(self):
        for trapped in (False, True):
            with self.subTest(trapped=trapped):
                result = self.compare(["10000"], ["20000"], trapped)
                self.assertEqual(result["counts"], {"total_changed": 1})

    def test_small_differences_are_not_rounded_to_zero(self):
        for trapped in (False, True):
            with self.subTest(trapped=trapped):
                result = self.compare(["0." + "0" * 40 + "1"],
                                      ["0." + "0" * 40 + "2"], trapped)
                self.assertEqual(result["counts"], {"total_changed": 1})

    def test_exact_cancellation_does_not_overflow(self):
        for trapped in (False, True):
            with self.subTest(trapped=trapped):
                result = self.compare(["10000", "-10000"], ["0", "0"], trapped)
                self.assertTrue(result["ok"])

    def test_valid_equal_totals_do_not_trigger_caller_traps(self):
        for trapped in (False, True):
            with self.subTest(trapped=trapped):
                result = self.compare(["0.000001", "0.000002"], ["0.000003", "0"], trapped)
                self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
