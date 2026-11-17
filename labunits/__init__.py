"""labunits -- batch-convert lab CSV columns between conventional and SI units.

Only analytes whose conversion factor was verified against two
independent authorities are converted. Analytes without a fixed
factor are refused, with the reason. Conversion only: no reference
ranges, no flagging, no interpretation.
"""

__version__ = "0.1.0"
