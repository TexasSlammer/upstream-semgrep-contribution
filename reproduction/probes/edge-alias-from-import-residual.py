# DOCUMENTED RESIDUAL GAP: aliased from-import is not resolved
# by the bare-name branch (import binds CL, not CLoader). Expected: no match.
# See CASE-STUDY.md section 10.

from yaml import CLoader as CL
yaml.load("payload", CL)
