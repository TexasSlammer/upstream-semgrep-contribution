import yaml
class Loader(yaml.SafeLoader):
    pass
yaml.load("color: blue", Loader)
