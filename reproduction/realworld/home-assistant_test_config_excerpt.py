        patch.object(os, "system") as system_mock,
        contextlib.suppress(HomeAssistantError),
    ):
        config_util.load_yaml_config_file(YAML_PATH)

    assert len(system_mock.mock_calls) == 0

    # Here we validate that the test above is a good test
    # since previously the syntax was not valid
    with (
        open(YAML_PATH, encoding="utf8") as fp,
        patch.object(os, "system") as system_mock,
    ):
        list(yaml.unsafe_load_all(fp))

    assert len(system_mock.mock_calls) == 1


def test_load_yaml_config_preserves_key_order() -> None:
    """Test removal of library."""
    with open(YAML_PATH, "w", encoding="utf8") as fp:
        fp.write("hello: 2\n")
        fp.write("world: 1\n")

    assert list(config_util.load_yaml_config_file(YAML_PATH).items()) == [
        ("hello", 2),
