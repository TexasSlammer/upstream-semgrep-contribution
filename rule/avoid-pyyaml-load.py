import yaml


#ruleid:avoid-pyyaml-load
yaml.unsafe_load("!!python/object/new:os.system [echo EXPLOIT!]")

def thing(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.unsafe_load("!!python/object/new:os.system [echo EXPLOIT!]", **kwargs)

def other_thing(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", Loader=yaml.Loader, **kwargs)

def other_thing_two(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", Loader=yaml.UnsafeLoader, **kwargs)

def other_thing_three(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.load("!!python/object/new:os.system [echo EXPLOIT!]", Loader=yaml.CLoader, **kwargs)

def other_thing_four(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.load_all("!!python/object/new:os.system [echo EXPLOIT!]", Loader=yaml.Loader, **kwargs)

def other_thing_five(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.load_all("!!python/object/new:os.system [echo EXPLOIT!]", Loader=yaml.UnsafeLoader, **kwargs)

def other_thing_six(**kwargs):
    #ruleid:avoid-pyyaml-load
    yaml.load_all("!!python/object/new:os.system [echo EXPLOIT!]", Loader=yaml.CLoader, **kwargs)

def this_is_ok(stream):
    #ok:avoid-pyyaml-load
    return yaml.load(stream, Loader=yaml.CSafeLoader)

def this_is_also_ok(stream):
    #ok:avoid-pyyaml-load
    return yaml.load(stream, Loader=yaml.SafeLoader)

def this_is_additionally_ok(stream):
    #ok:avoid-pyyaml-load
    return yaml.load_all(stream, Loader=yaml.CSafeLoader)

def this_is_ok_too(stream):
    #ok:avoid-pyyaml-load
    return yaml.load_all(stream, Loader=yaml.SafeLoader)

def this_is_ok_as_well(stream):
    #ok:avoid-pyyaml-load
    return yaml.load(stream, Loader=yaml.BaseLoader)

def this_is_ok_too_two(stream):
    #ok:avoid-pyyaml-load
    return yaml.load_all(stream, Loader=yaml.BaseLoader)

def check_ruamel_yaml():
    from ruamel.yaml import YAML
    yaml = YAML(typ="rt")
    # ok:avoid-pyyaml-load
    yaml.load("thing.yaml")
    # ok:avoid-pyyaml-load
    yaml.load_all("thing.yaml")


def unsafe_load_all_is_unsafe(stream):
    #ruleid:avoid-pyyaml-load
    yaml.unsafe_load_all(stream)


def unsafe_load_all_from_import(stream):
    from yaml import unsafe_load_all
    #ruleid:avoid-pyyaml-load
    unsafe_load_all(stream)


def positional_loader_module_qualified(stream):
    #ruleid:avoid-pyyaml-load
    yaml.load(stream, yaml.Loader)


def positional_unsafe_loader_module_qualified(stream):
    #ruleid:avoid-pyyaml-load
    yaml.load(stream, yaml.UnsafeLoader)


def positional_cloader_load_all_module_qualified(stream):
    #ruleid:avoid-pyyaml-load
    yaml.load_all(stream, yaml.CLoader)


def positional_loader_from_import(stream):
    from yaml import CLoader
    #ruleid:avoid-pyyaml-load
    yaml.load(stream, CLoader)


def positional_loader_from_import_multi_name(stream):
    from yaml import load, UnsafeLoader
    #ruleid:avoid-pyyaml-load
    load(stream, UnsafeLoader)


def positional_load_all_loader_from_import(stream):
    from yaml import Loader
    #ruleid:avoid-pyyaml-load
    yaml.load_all(stream, Loader)


def positional_safe_loaders_module_qualified(stream):
    #ok:avoid-pyyaml-load
    yaml.load(stream, yaml.SafeLoader)
    #ok:avoid-pyyaml-load
    yaml.load(stream, yaml.CSafeLoader)
    #ok:avoid-pyyaml-load
    yaml.load_all(stream, yaml.BaseLoader)


def positional_loader_from_import_safe(stream):
    from yaml import SafeLoader
    #ok:avoid-pyyaml-load
    yaml.load(stream, SafeLoader)


def full_load_is_out_of_scope(stream):
    #ok:avoid-pyyaml-load
    yaml.full_load(stream)


def local_safe_loader_shadow(stream):
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    #ok:avoid-pyyaml-load
    yaml.load(stream, Loader)
