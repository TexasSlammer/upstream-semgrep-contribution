# EDGE-A: multi-name single-line from-import + positional (worst-case residual)
from yaml import load, CLoader
load("!!python/object/new:os.system [echo EXPLOIT!]", CLoader)

# EDGE-B (MUST NOT MATCH): local safe Loader subclass, only `import yaml` present.
import yaml
class Loader(yaml.SafeLoader):
    pass
yaml.load("color: blue", Loader)

# EDGE-C (MUST NOT MATCH): yaml from-import elsewhere in file, local safe class here.
from yaml import safe_load
import yaml
class CLoader(yaml.SafeLoader):
    pass
yaml.load("color: blue", CLoader)
