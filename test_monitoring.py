from monitor import load_config
import pytest

config_directory = "ex-configs/"


# These tests are for the load_config function, which is responsible for loading and validating the YAML configuration file.

def test_invalid_yaml():
    result = load_config(config_directory + "invalid-yaml.yml")
    assert result is None

def test_empty_yaml():
    result = load_config(config_directory + "empty.yml")
    assert result == None

def test_missing_name():
    result = load_config(config_directory + "missing-name.yml")
    assert result is None

def test_missing_url():
    result = load_config(config_directory + "missing-url.yml")
    assert result is None

def test_valid_yaml():
    result = load_config(config_directory + "generic_sample.yml")
    assert result is not None
    assert len(result) == 5
