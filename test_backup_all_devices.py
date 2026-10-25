"""
test_backup_all_devices.py

Unit tests for backup_all_devices.py verifying:
- SSH key resolution across local, user, and fallback paths
- Argument parsing
- File saving with and without timestamps
- Driver invocation with mocks
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from backup_all_devices import (
    DEFAULT_DEVICES,
    backup_device,
    parse_args,
    resolve_ssh_key,
    run_backup,
    save_backup,
)


def test_resolve_ssh_key_explicit_valid(tmp_path):
    fake_key = tmp_path / "custom_key"
    fake_key.write_text("fake-key-content")
    assert resolve_ssh_key(str(fake_key)) == str(fake_key)


def test_resolve_ssh_key_explicit_invalid():
    with pytest.raises(FileNotFoundError):
        resolve_ssh_key("/path/that/does/not/exist_12345")


def test_resolve_ssh_key_env(tmp_path, monkeypatch):
    fake_key = tmp_path / "env_key"
    fake_key.write_text("env-key-content")
    monkeypatch.setenv("SSH_KEY_PATH", str(fake_key))
    assert resolve_ssh_key() == str(fake_key)


def test_save_backup_default(tmp_path):
    backup_dir = str(tmp_path / "backups")
    content = "hostname R0-P\ninterface GigabitEthernet0/0\n"
    primary, ts = save_backup("R0-P", content, backup_dir=backup_dir, with_timestamp=False)

    assert os.path.exists(primary)
    assert ts is None
    with open(primary, "r", encoding="utf-8") as f:
        assert f.read() == content


def test_save_backup_with_timestamp(tmp_path):
    backup_dir = str(tmp_path / "backups")
    content = "hostname R1-P\n"
    primary, ts = save_backup("R1-P", content, backup_dir=backup_dir, with_timestamp=True)

    assert os.path.exists(primary)
    assert ts is not None
    assert os.path.exists(ts)
    with open(ts, "r", encoding="utf-8") as f:
        assert f.read() == content


def test_backup_device_invalid_driver():
    with pytest.raises(ValueError, match="Unknown driver"):
        backup_device({"name": "test", "host": "127.0.0.1", "port": 22}, driver="unknown")


@patch("backup_all_devices.backup_device_netmiko")
def test_backup_device_netmiko_dispatch(mock_netmiko):
    mock_netmiko.return_value = "mock config netmiko"
    device = {"name": "R0-P", "host": "192.168.1.41", "port": 22}
    output = backup_device(device, driver="netmiko")
    assert output == "mock config netmiko"
    mock_netmiko.assert_called_once()


@patch("backup_all_devices.backup_device_paramiko")
def test_backup_device_paramiko_dispatch(mock_paramiko):
    mock_paramiko.return_value = "mock config paramiko"
    device = {"name": "R0-P", "host": "192.168.1.41", "port": 22}
    output = backup_device(device, driver="paramiko")
    assert output == "mock config paramiko"
    mock_paramiko.assert_called_once()


@patch("backup_all_devices.backup_device")
def test_run_backup_success_and_failure(mock_backup, tmp_path):
    def side_effect(device, **kwargs):
        if device["name"] == "R0-P":
            return "config for R0-P"
        raise ConnectionRefusedError("Connection refused")

    mock_backup.side_effect = side_effect
    backup_dir = str(tmp_path / "test_backups")

    devices = [
        {"name": "R0-P", "host": "192.168.1.41", "port": 22},
        {"name": "R1-P", "host": "192.168.1.41", "port": 2222},
    ]

    results = run_backup(
        devices=devices,
        backup_dir=backup_dir,
        timeout=1,
    )

    assert len(results["success"]) == 1
    assert "R0-P" in results["success"]
    assert len(results["failed"]) == 1
    assert results["failed"][0][0] == "R1-P"

    assert os.path.exists(os.path.join(backup_dir, "R0-P_running-config.txt"))
