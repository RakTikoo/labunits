"""Tests for labunits.

Run from the repo root:  python3 run_tests.py

The factor-verification test is the important one: for every molar
analyte, it re-derives the factor from the analyte's molar mass
(factor = 10**mw_power / molar_mass, the independent second
authority) and asserts the shipped AMA factor agrees within 1%.
If a factor is ever edited without re-verification, this fails.
"""

import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from labunits import core  # noqa: E402
from labunits.analytes import ANALYTES, REFUSED  # noqa: E402


def run_cli(*argv):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "labunits", *argv],
        capture_output=True, text=True, cwd=ROOT, env=env)


class FactorVerificationTests(unittest.TestCase):
    def test_molar_factors_match_molar_mass_derivation(self):
        checked = 0
        for key, info in ANALYTES.items():
            if info["molar_mass"] is None:
                continue
            derived = 10 ** info["mw_power"] / info["molar_mass"]
            rel = abs(info["factor"] - derived) / derived
            self.assertLess(
                rel, 0.01,
                f"{key}: shipped AMA factor {info['factor']} disagrees "
                f"with molar-mass derivation {derived:.6g} by "
                f"{rel * 100:.2f}%")
            checked += 1
        self.assertGreaterEqual(checked, 40)

    def test_every_shipped_analyte_has_two_sources(self):
        for key, info in ANALYTES.items():
            self.assertTrue(info["ama"], key)
            self.assertTrue(info["second"], key)

    def test_shipped_count_in_range(self):
        # Task scope: ~40-60 analytes including the two specials.
        total = len(ANALYTES) + 2  # + hba1c, bun
        self.assertGreaterEqual(total, 40)
        self.assertLessEqual(total, 62)


class RoundTripTests(unittest.TestCase):
    def test_round_trip_every_linear_analyte(self):
        for key in ANALYTES:
            for value in (0.37, 1.0, 12.5, 100.0, 999.0):
                si = core.convert_value(key, value, "conventional", "si")
                back = core.convert_value(key, si, "si", "conventional")
                self.assertAlmostEqual(back, value, places=7,
                                       msg=f"{key} round trip")

    def test_round_trip_specials(self):
        for key in ("hba1c", "bun"):
            for value in (3.1, 7.0, 42.0):
                si = core.convert_value(key, value, "conventional", "si")
                back = core.convert_value(key, si, "si", "conventional")
                self.assertAlmostEqual(back, value, places=7, msg=key)


class WorkedPairTests(unittest.TestCase):
    def test_published_worked_pairs(self):
        # Glucose 100 mg/dL = 5.55 mmol/L; cholesterol 200 = 5.17;
        # NGSP table: 7.0% = 53 mmol/mol, 6.5% = 48; BUN 14 = urea 5.0.
        for key, conv, expected, tol in core.WORKED_PAIRS:
            got = core.convert_value(key, conv, "conventional", "si")
            self.assertAlmostEqual(got, expected, delta=tol,
                                   msg=f"{key}: {conv} -> {got}")

    def test_check_command_passes(self):
        failures, _ = core.run_check()
        self.assertEqual(failures, [])


class HbA1cTests(unittest.TestCase):
    def test_master_equation_forward(self):
        # (7.0 - 2.152) / 0.09148 = 52.99... -> NGSP table value 53.
        got = core.convert_value("hba1c", 7.0, "conventional", "si")
        self.assertAlmostEqual(got, 53.0, delta=0.1)
        self.assertEqual(round(got), 53)

    def test_master_equation_inverse(self):
        got = core.convert_value("hba1c", 53.0, "si", "conventional")
        self.assertAlmostEqual(got, 7.0, delta=0.01)

    def test_not_a_factor(self):
        # An affine equation is not proportional: doubling the %
        # must NOT double the mmol/mol.
        a = core.convert_value("hba1c", 5.0, "conventional", "si")
        b = core.convert_value("hba1c", 10.0, "conventional", "si")
        self.assertNotAlmostEqual(b, 2 * a, places=1)


class BunUreaTests(unittest.TestCase):
    def test_bun_to_urea_mmol(self):
        self.assertAlmostEqual(
            core.convert_value("bun", 14.0, "conventional", "si"),
            5.0, delta=0.01)
        self.assertAlmostEqual(
            core.convert_value("bun", 10.0, "conventional", "si"),
            3.57, delta=0.001)

    def test_bun_to_urea_mgdl_is_a_different_number(self):
        # The classic silent error: BUN 14 mg/dL is urea 30 mg/dL
        # (x2.14) but urea 5.0 mmol/L (x0.357). Both must hold.
        self.assertAlmostEqual(core.bun_to_urea_mgdl(14.0), 29.96,
                               delta=0.01)
        self.assertAlmostEqual(core.urea_mgdl_to_bun(29.96), 14.0,
                               delta=0.01)

    def test_urea_itself_is_a_separate_analyte(self):
        # Urea reported as the whole molecule in mg/dL uses 0.1665,
        # NOT the BUN factor 0.357.
        got = core.convert_value("urea", 60.0, "conventional", "si")
        self.assertAlmostEqual(got, 9.99, delta=0.01)
        self.assertNotAlmostEqual(
            got, core.convert_value("bun", 60.0, "conventional", "si"),
            places=1)

    def test_bun_output_is_labelled_urea(self):
        info = core.analyte_info("bun")
        self.assertIn("urea", info["si_unit"])


class RefusalTests(unittest.TestCase):
    def test_refused_analytes_raise_with_reason(self):
        for name in ("insulin", "alt", "lpa", "ammonia", "lipase"):
            with self.assertRaises(core.LabunitsError, msg=name) as ctx:
                core.resolve_analyte(name)
            self.assertIn("refused", str(ctx.exception))

    def test_refused_table_is_enforced(self):
        # Every name in REFUSED must actually be refused.
        for name in REFUSED:
            with self.assertRaises(core.LabunitsError, msg=name):
                core.resolve_analyte(name)

    def test_unknown_analyte_refused(self):
        with self.assertRaises(core.LabunitsError):
            core.resolve_analyte("unobtainium")

    def test_cli_refuses_insulin(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.csv"
            src.write_text("patient,insulin\nP1,12\n")
            out = Path(td) / "out.csv"
            proc = run_cli("convert", str(src), "--columns", "insulin",
                           "--from", "conventional", "--to", "si",
                           "--out", str(out))
            self.assertEqual(proc.returncode, 2)
            self.assertIn("refused", proc.stderr)
            self.assertFalse(out.exists())

    def test_same_system_refused(self):
        with self.assertRaises(core.LabunitsError):
            core.convert_value("glucose", 100.0, "si", "si")

    def test_lpa_standard_spelling_refused_not_unknown(self):
        # 'Lp(a)' is the standard clinical spelling; it must get the
        # specific Lp(a) refusal, not a misleading 'unknown analyte'.
        for name in ("Lp(a)", "lipoprotein(a)", "lp_a"):
            with self.assertRaises(core.LabunitsError, msg=name) as ctx:
                core.resolve_analyte(name)
            self.assertIn("refused", str(ctx.exception), name)

    def test_bare_and_full_names_refused(self):
        for name in ("troponin", "creatine_kinase",
                     "alanine aminotransferase"):
            with self.assertRaises(core.LabunitsError, msg=name) as ctx:
                core.resolve_analyte(name)
            self.assertIn("refused", str(ctx.exception), name)

    def test_urea_nitrogen_is_bun_alias(self):
        # 'Urea nitrogen' is the AMA table's own name for BUN.
        self.assertEqual(core.resolve_analyte("urea_nitrogen"), "bun")


class InvalidValueTests(unittest.TestCase):
    def test_negative_and_nonfinite_values_refused(self):
        import math
        for bad in (-1.0, -100.0, math.nan, math.inf, -math.inf):
            for key in ("glucose", "hba1c", "bun"):
                with self.assertRaises(core.LabunitsError,
                                       msg=f"{key} {bad}"):
                    core.convert_value(key, bad, "conventional", "si")
                with self.assertRaises(core.LabunitsError,
                                       msg=f"{key} {bad} reverse"):
                    core.convert_value(key, bad, "si", "conventional")

    def test_zero_is_allowed(self):
        self.assertEqual(
            core.convert_value("glucose", 0.0, "conventional", "si"),
            0.0)

    def test_bun_helpers_reject_invalid(self):
        with self.assertRaises(core.LabunitsError):
            core.bun_to_urea_mgdl(-14.0)
        with self.assertRaises(core.LabunitsError):
            core.urea_mgdl_to_bun(float("nan"))


class CliConvertTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.dir = Path(self.td.name)

    def _write(self, name, text):
        p = self.dir / name
        p.write_text(text)
        return p

    def test_convert_columns_mode(self):
        src = self._write(
            "labs.csv",
            "patient,glucose,creatinine\nP1,100,1.0\nP2,200,2.0\n")
        out = self.dir / "out.csv"
        proc = run_cli("convert", str(src), "--columns",
                       "glucose,creatinine", "--from", "conventional",
                       "--to", "si", "--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["glucose"], "100")  # original kept
        self.assertAlmostEqual(
            float(rows[0]["glucose__mmol_L"]), 5.55, delta=0.001)
        self.assertAlmostEqual(
            float(rows[1]["creatinine__umol_L"]), 176.8, delta=0.01)
        self.assertIn("0.0555", rows[0]["glucose__factor"])

    def test_convert_reverse_direction(self):
        src = self._write("labs.csv", "patient,glucose\nP1,5.55\n")
        out = self.dir / "out.csv"
        proc = run_cli("convert", str(src), "--columns", "glucose",
                       "--from", "si", "--to", "conventional",
                       "--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertAlmostEqual(
            float(rows[0]["glucose__mg_dL"]), 100.0, delta=0.01)

    def test_convert_spec_mode_renamed_columns(self):
        src = self._write(
            "labs.csv", "patient,glucose_mgdl,a1c_pct\nP1,100,7.0\n")
        spec = self._write(
            "spec.csv",
            "analyte,column\nglucose,glucose_mgdl\nhba1c,a1c_pct\n")
        out = self.dir / "out.csv"
        proc = run_cli("convert", str(src), "--spec", str(spec),
                       "--from", "conventional", "--to", "si",
                       "--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertAlmostEqual(
            float(rows[0]["a1c_pct__mmol_mol_IFCC"]), 53.0, delta=0.1)

    def test_missing_direction_refused(self):
        src = self._write("labs.csv", "patient,glucose\nP1,100\n")
        proc = run_cli("convert", str(src), "--columns", "glucose",
                       "--out", str(self.dir / "o.csv"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("refuses to guess", proc.stderr)

    def test_missing_column_is_clean_error(self):
        src = self._write("labs.csv", "patient,glucose\nP1,100\n")
        proc = run_cli("convert", str(src), "--columns", "creatinine",
                       "--from", "conventional", "--to", "si",
                       "--out", str(self.dir / "o.csv"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not found", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_non_numeric_cell_is_clean_error(self):
        src = self._write("labs.csv", "patient,glucose\nP1,high\n")
        proc = run_cli("convert", str(src), "--columns", "glucose",
                       "--from", "conventional", "--to", "si",
                       "--out", str(self.dir / "o.csv"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not a number", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_empty_cells_pass_through_empty(self):
        src = self._write("labs.csv", "patient,glucose\nP1,\nP2,100\n")
        out = self.dir / "out.csv"
        proc = run_cli("convert", str(src), "--columns", "glucose",
                       "--from", "conventional", "--to", "si",
                       "--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with out.open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["glucose__mmol_L"], "")

    def test_invalid_cells_are_clean_errors(self):
        # float() would parse every one of these; none is a lab value.
        for cell in ("-100", "nan", "inf", "-inf", "1_000", "1e999"):
            src = self._write("labs.csv",
                              f"patient,glucose\nP1,{cell}\n")
            out = self.dir / "o.csv"
            proc = run_cli("convert", str(src), "--columns", "glucose",
                           "--from", "conventional", "--to", "si",
                           "--out", str(out))
            self.assertEqual(proc.returncode, 2, cell)
            self.assertNotIn("Traceback", proc.stderr, cell)
            self.assertFalse(out.exists(), cell)

    def test_out_equal_to_input_refused(self):
        src = self._write("labs.csv", "patient,glucose\nP1,100\n")
        proc = run_cli("convert", str(src), "--columns", "glucose",
                       "--from", "conventional", "--to", "si",
                       "--out", str(src))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("input file", proc.stderr)
        self.assertEqual(src.read_text(), "patient,glucose\nP1,100\n")

    def test_convert_one(self):
        proc = run_cli("convert-one", "--analyte", "glucose",
                       "--value", "100", "--from", "conventional",
                       "--to", "si")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("5.55", proc.stdout)

    def test_check_subcommand(self):
        proc = run_cli("check")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_list_subcommand(self):
        proc = run_cli("list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("glucose", proc.stdout)
        self.assertIn("insulin", proc.stdout)  # in the refused list


if __name__ == "__main__":
    unittest.main()
