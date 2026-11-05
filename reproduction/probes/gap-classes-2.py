# Probe 2: confirm additional gap surface + true-negative guards.

# GAP-A: unsafe_load_all on module object
import yaml
yaml.unsafe_load_all("!!python/object/new:os.system [echo EXPLOIT!]")

# GAP-B: unsafe_load_all via from-import (engine already resolves from-imports)
from yaml import unsafe_load_all
unsafe_load_all("!!python/object/new:os.system [echo EXPLOIT!]")

# GAP-C: positional UnsafeLoader on load (most explicit unsafe loader, positional form)
import yaml
yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", yaml.UnsafeLoader)

# GAP-D: positional Loader on load via from-import style
from yaml import load
from yaml import CLoader
load("!!python/object/new:os.system [echo EXPLOIT!]", CLoader)

# TN-GUARD-1: positional SafeLoader on module object
import yaml
yaml.load("color: blue", yaml.SafeLoader)

# TN-GUARD-2: positional CSafeLoader
import yaml
yaml.load_all("color: blue", yaml.CSafeLoader)

# TN-GUARD-3: positional BaseLoader
import yaml
yaml.load("color: blue", yaml.BaseLoader)

# OBS-1 (engine observation, not part of this fix): same-named API on an unrelated module.
# If this fires, the from-import resolution is name-based; noted as an existing engine
# tradeoff in the write-up limitations section.
from mypackage import unsafe_load
unsafe_load("harmless data")

# POSITIVE CONTROL: canonical form the current rule must catch (proves harness works).
import yaml
yaml.unsafe_load("!!python/object/new:os.system [echo EXPLOIT!]")

