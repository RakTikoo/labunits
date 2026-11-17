"""Core conversion logic for labunits.

Design rule (from the research that scoped this tool): compute the
number, never interpret it. No reference ranges, no flagging, no
"abnormal" calls -- conversion only, with the factor used written
into the output so every converted value can be checked by hand.

Two conversions are NOT simple factors and are handled explicitly:

1. HbA1c -- NGSP % <-> IFCC mmol/mol is an affine master equation,
   not a multiplication:
       NGSP (%)        = 0.09148 * IFCC (mmol/mol) + 2.152
       IFCC (mmol/mol) = (NGSP (%) - 2.152) / 0.09148
   Source: NGSP, "IFCC Standardization of HbA1c" (the NGSP-IFCC
   master equation, from Hoelzel et al., Clin Chem 2004;50:166-174).
   The AMA Manual of Style does NOT give a factor for HbA1c (it
   lists only % -> proportion of total haemoglobin), which is
   exactly why a factor-based tool must not treat HbA1c as one.

2. BUN <-> urea -- these are DIFFERENT analytes, not two units of
   one analyte. US labs report blood urea nitrogen: the mass of the
   nitrogen inside urea only. SI labs report urea: the whole
   molecule. One urea molecule (molar mass 60.056) carries two
   nitrogen atoms (28.014), so:
       urea (mmol/L) = BUN (mg/dL) * 10 / 28.014 = BUN * 0.357
       urea (mg/dL)  = BUN (mg/dL) * 60.056 / 28.014 = BUN * 2.14
   Sources: AMA Manual of Style, Table 17.5-2 ("Urea nitrogen,
   mg/dL, factor 0.357, mmol/L"); Higgins, "Urea and the clinical
   value of measuring blood urea concentration", acutecaretesting.org
   (Radiometer), which derives 0.357 = 10/28 and 2.14 = 60/28 from
   first principles; PMC conversion tables agree (0.357).
   A column labelled `bun` therefore converts to a column labelled
   *urea* mmol/L -- the analyte name changes on purpose, and the
   output column name says so.
"""

from __future__ import annotations

import math

from .analytes import ALIASES, ANALYTES, REFUSED

SYSTEMS = ("conventional", "si")

# --- HbA1c master equation constants (NGSP) ---------------------------
HBA1C_SLOPE = 0.09148
HBA1C_INTERCEPT = 2.152

# --- BUN / urea constants ---------------------------------------------
BUN_TO_UREA_MMOL_FACTOR = 0.357   # AMA Table 17.5-2; derived 10/28.014 = 0.35700
BUN_TO_UREA_MGDL_FACTOR = 2.14    # derived 60.056/28.014 = 2.1439, quoted as 2.14


class LabunitsError(Exception):
    """A clean, user-facing error (never a traceback)."""


def resolve_analyte(name):
    """Return the canonical analyte key, or raise with an explanation.

    Refused analytes raise with their specific refusal reason;
    unknown names raise listing what is available.
    """
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    key = ALIASES.get(key, key)
    if key in ("hba1c", "bun"):
        return key
    if key in ANALYTES:
        return key
    if key in REFUSED:
        raise LabunitsError(f"refused: {name!r} -- {REFUSED[key]}")
    # Also refuse if the raw spelling hits the refused table.
    raw = name.strip().lower().replace("-", "_").replace(" ", "_")
    if raw in REFUSED:
        raise LabunitsError(f"refused: {name!r} -- {REFUSED[raw]}")
    available = ", ".join(sorted(list(ANALYTES) + ["bun", "hba1c"]))
    raise LabunitsError(
        f"unknown analyte {name!r}. labunits only converts analytes "
        f"whose factor it has verified twice. Available: {available}. "
        f"Refused (no fixed factor): {', '.join(sorted(REFUSED))}.")


def analyte_info(key):
    """Unit/factor description for a canonical key, both systems."""
    if key == "hba1c":
        return {
            "key": "hba1c", "name": "Hemoglobin A1c (HbA1c)",
            "conv_unit": "% (NGSP)", "si_unit": "mmol/mol (IFCC)",
            "factor": None,
            "formula_conv_to_si": "mmol/mol = (% - 2.152) / 0.09148",
            "formula_si_to_conv": "% = 0.09148 * mmol/mol + 2.152",
            "source": "NGSP-IFCC master equation (NGSP, IFCC "
                      "Standardization of HbA1c; Hoelzel et al. 2004)",
        }
    if key == "bun":
        return {
            "key": "bun",
            "name": "Blood urea nitrogen (BUN) -> urea",
            "conv_unit": "mg/dL (as nitrogen)", "si_unit": "mmol/L (urea)",
            "factor": BUN_TO_UREA_MMOL_FACTOR,
            "formula_conv_to_si": "urea mmol/L = BUN mg/dL * 0.357",
            "formula_si_to_conv": "BUN mg/dL = urea mmol/L / 0.357",
            "source": "AMA Manual of Style, Table 17.5-2 (urea "
                      "nitrogen, 0.357); derivation 10/28.014 in "
                      "Higgins, acutecaretesting.org. BUN and urea "
                      "are different analytes -- see README",
        }
    info = dict(ANALYTES[key])
    info["formula_conv_to_si"] = (
        f"{info['si_unit']} = {info['conv_unit']} * {info['factor']:g}")
    info["formula_si_to_conv"] = (
        f"{info['conv_unit']} = {info['si_unit']} / {info['factor']:g}")
    info["source"] = f"{info['ama']}; verified against: {info['second']}"
    return info


def _check_value(value):
    """Reject values no laboratory measurement can take.

    A concentration, a percentage or an amount-of-substance ratio is
    never negative and never NaN/infinite. float() happily parses
    'nan', 'inf' and '-100' out of a CSV cell, so without this check
    those would be silently 'converted' into the output -- exactly
    the silent-garbage failure this tool exists to prevent.
    """
    if not math.isfinite(value):
        raise LabunitsError(
            f"value {value!r} is not a finite number -- labunits "
            "converts measured values only.")
    if value < 0:
        raise LabunitsError(
            f"value {value:g} is negative -- a laboratory result "
            "cannot be negative, so labunits refuses to convert it "
            "rather than write a plausible-looking wrong number.")


def convert_value(key, value, from_system, to_system):
    """Convert one numeric value. Systems must differ."""
    _check_value(value)
    if from_system not in SYSTEMS or to_system not in SYSTEMS:
        raise LabunitsError(
            f"systems must be 'conventional' or 'si', got "
            f"{from_system!r} -> {to_system!r}")
    if from_system == to_system:
        raise LabunitsError(
            "from and to systems are the same -- nothing to convert. "
            "State two different systems: --from conventional --to si "
            "or --from si --to conventional.")
    if key == "hba1c":
        if from_system == "conventional":   # % -> mmol/mol
            return (value - HBA1C_INTERCEPT) / HBA1C_SLOPE
        return HBA1C_SLOPE * value + HBA1C_INTERCEPT
    if key == "bun":
        if from_system == "conventional":
            return value * BUN_TO_UREA_MMOL_FACTOR
        return value / BUN_TO_UREA_MMOL_FACTOR
    factor = ANALYTES[key]["factor"]
    if from_system == "conventional":
        return value * factor
    return value / factor


def bun_to_urea_mgdl(bun_mgdl):
    """BUN (mg/dL, nitrogen only) -> urea (mg/dL, whole molecule)."""
    _check_value(bun_mgdl)
    return bun_mgdl * BUN_TO_UREA_MGDL_FACTOR


def urea_mgdl_to_bun(urea_mgdl):
    _check_value(urea_mgdl)
    return urea_mgdl / BUN_TO_UREA_MGDL_FACTOR


def factor_label(key, from_system):
    """The 'factor used' string written into output factor columns."""
    info = analyte_info(key)
    if from_system == "conventional":
        return info["formula_conv_to_si"]
    return info["formula_si_to_conv"]


def target_unit(key, to_system):
    info = analyte_info(key)
    return info["si_unit"] if to_system == "si" else info["conv_unit"]


def format_value(value):
    """Stable, compact formatting for output CSVs (6 significant digits)."""
    return f"{value:.6g}"


# --- built-in self-check (labunits check) ------------------------------

# Published worked pairs: (analyte, conventional value, expected SI
# value, tolerance). Sources: AMA-cited converter worked tables
# (HomeBloodTestGuide, factors per AMA Manual of Style), NGSP HbA1c
# table, Higgins (acutecaretesting.org) for BUN, PMC conversion table.
WORKED_PAIRS = [
    ("glucose", 100.0, 5.55, 0.01),
    ("cholesterol_total", 200.0, 5.17, 0.02),
    ("triglycerides", 150.0, 1.69, 0.02),
    ("creatinine", 1.0, 88.4, 0.1),
    ("vitamin_d_25oh", 30.0, 74.9, 0.2),
    ("testosterone", 500.0, 17.3, 0.1),
    ("hba1c", 7.0, 53.0, 0.6),
    ("hba1c", 6.5, 48.0, 0.6),
    ("bun", 14.0, 5.0, 0.05),
    ("bilirubin_total", 1.0, 17.1, 0.1),
    ("calcium_total", 10.0, 2.5, 0.01),
    ("urea", 60.0, 10.0, 0.05),
]


def run_check():
    """Return (failures, lines) for the built-in worked pairs."""
    failures = []
    lines = []
    for key, conv, expected_si, tol in WORKED_PAIRS:
        got = convert_value(key, conv, "conventional", "si")
        ok = abs(got - expected_si) <= tol
        if not ok:
            failures.append(key)
        info = analyte_info(key)
        lines.append(
            f"  {info['name']}: {conv:g} {info['conv_unit']} -> "
            f"{got:.4g} {info['si_unit']} (published: {expected_si:g}) "
            f"{'PASS' if ok else 'FAIL'}")
    return failures, lines
