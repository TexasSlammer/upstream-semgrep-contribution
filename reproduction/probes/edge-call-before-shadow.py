# DOCUMENTED EDGE BEHAVIOR: the call precedes the local class definition,
# so the shadow exclusion cannot apply. Flagging is semantically correct
# (at call time the name still refers to yaml.CLoader). Expected: match at line 6.

from yaml import CLoader
yaml.load("payload", CLoader)

class CLoader(yaml.SafeLoader):
    pass
