from yaml import safe_load
import yaml
class CLoader(yaml.SafeLoader):
    pass
yaml.load("color: blue", CLoader)
