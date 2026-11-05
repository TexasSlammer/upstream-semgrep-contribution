# Probe corpus: hypothesized false negatives (FN1..FN7) and controls (TP-CTRL, TN1..TN4)
# for python.lang.security.deserialization.avoid-pyyaml-load (current develop state).

# --- HYPOTHESIZED FALSE NEGATIVES ---

# FN1: from-import of unsafe_load; pattern-inside "import yaml" never matches this file.
from yaml import unsafe_load
unsafe_load("!!python/object/new:os.system [echo EXPLOIT!]")

# FN2: from-import of load + UnsafeLoader, keyword Loader.
from yaml import load
from yaml import UnsafeLoader
load("!!python/object/new:os.system [echo EXPLOIT!]", Loader=UnsafeLoader)

# FN3: from-import of load + Loader (the classic unsafe default loader).
from yaml import load, Loader
load("!!python/object/new:os.system [echo EXPLOIT!]", Loader=Loader)

# FN4: module alias; y.unsafe_load is identical to yaml.unsafe_load.
import yaml as y
y.unsafe_load("!!python/object/new:os.system [echo EXPLOIT!]")

# FN5: module alias with keyword Loader referencing the alias.
import yaml as _y
_y.load("!!python/object/new:os.system [echo EXPLOIT!]", Loader=_y.UnsafeLoader)

# FN6: positional Loader argument (legal: load(stream, Loader)).
import yaml
yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", yaml.Loader)

# FN7: positional Loader on load_all.
import yaml
yaml.load_all("!!python/object/new:os.system [echo EXPLOIT!]", yaml.CLoader)

# --- CONTROL TRUE POSITIVE (rule must keep matching) ---

# TP-CTRL: the canonical form the current rule catches.
import yaml
yaml.unsafe_load("!!python/object/new:os.system [echo EXPLOIT!]")

# --- TRUE NEGATIVES (both current and improved rule must stay silent) ---

# TN1: safe_load via from-import.
from yaml import safe_load
safe_load("color: blue")

# TN2: keyword SafeLoader.
import yaml
yaml.load("color: blue", Loader=yaml.SafeLoader)

# TN3: from-import of SafeLoader used as keyword.
from yaml import load
from yaml import SafeLoader
load("color: blue", Loader=SafeLoader)

# TN4: aliased module, safe loader.
import yaml as y
y.load("color: blue", Loader=y.SafeLoader)
