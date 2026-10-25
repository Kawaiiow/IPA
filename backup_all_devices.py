#!/usr/bin/env python3
"""
backup_all_devices.py

Automated backup script for all network devices in the IPA project.
Supports both Netmiko (default, recommended) and Paramiko backends.
Automatically locates SSH private keys across Linux, Windows, and macOS.

Devices:
  - R0-P (192.168.1.41:22)
  - R1-P (192.168.1.41:2222)
  - R2-P (192.168.1.41:2223)
  - S0-P (192.168.1.41:2224)
  - S1-P (192.168.1.41:2225)
"""

import argparse
from datetime import datetime
import os
import sys
import time

# Default host and user (can be overridden via environment variables or CLI arguments)
DEFAULT_HOST = os.environ.get("ROUTER_IP", "192.168.1.41")
DEFAULT_USER = os.environ.get("ROUTER_USER", "admin")
DEFAULT_BACKUP_DIR = "backups"

# Inventory of devices in the topology
DEFAULT_DEVICES = [
    {"name": "R0-P", "host": DEFAULT_HOST, "port": 22, "username": DEFAULT_USER},
    {"name": "R1-P", "host": DEFAULT_HOST, "port": 2222, "username": DEFAULT_USER},
    {"name": "R2-P", "host": DEFAULT_HOST, "port": 2223, "username": DEFAULT_USER},
    {"name": "S0-P", "host": DEFAULT_HOST, "port": 2224, "username": DEFAULT_USER},
    {"name": "S1-P", "host": DEFAULT_HOST, "port": 2225, "username": DEFAULT_USER},
]


def resolve_ssh_key(explicit_path=None):
    """
    Search for a valid SSH private key path across common locations.
    Checks explicit parameter, environment variables, local directory,
    user SSH folder, and legacy lab paths.
    """
    if explicit_path:
        expanded = os.path.expanduser(explicit_path)
        if os.path.exists(expanded):
            return expanded
        raise FileNotFoundError(f"Explicit SSH key file not found: {explicit_path}")

    env_path = os.environ.get("SSH_KEY_PATH")
    if env_path and os.path.exists(os.path.expanduser(env_path)):
        return os.path.expanduser(env_path)

    project_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(project_dir, "id_rsa"),
        os.path.join(project_dir, "cisco_rsa"),
        os.path.expanduser("~/.ssh/cisco_rsa"),
        os.path.expanduser("~/.ssh/id_rsa"),
        os.path.expanduser("~/.ssh/id_ed25519"),
        r"C:\Users\USER\Desktop\IPA_LAB\IPA_3\IPA\id_rsa",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def backup_device_netmiko(device, key_path=None, password=None, timeout=20):
    """
    Backup configuration using Netmiko (handles terminal length 0 and prompt detection).
    """
    from netmiko import ConnectHandler

    conn_params = {
        "device_type": "cisco_ios",
        "host": device["host"],
        "port": device["port"],
        "username": device.get("username", DEFAULT_USER),
        "conn_timeout": timeout,
        "banner_timeout": timeout,
        "auth_timeout": timeout,
        "fast_cli": False,
        "disable_sha2_fix": True,
        "disabled_algorithms": {"pubkeys": ["rsa-sha2-512", "rsa-sha2-256"]},
    }

    if key_path:
        conn_params["use_keys"] = True
        conn_params["key_file"] = key_path
    if password:
        conn_params["password"] = password

    net_connect = ConnectHandler(**conn_params)
    try:
        # Netmiko automatically runs terminal length 0 on connect
        config = net_connect.send_command("show running-config", read_timeout=35)
        return config
    finally:
        net_connect.disconnect()


def backup_device_paramiko(device, key_path=None, password=None, timeout=20):
    """
    Backup configuration using Paramiko.
    Disables pagination ('terminal length 0') so running-config is not truncated by --More--.
    """
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": device["host"],
        "port": device["port"],
        "username": device.get("username", DEFAULT_USER),
        "timeout": timeout,
        "look_for_keys": False,
        "allow_agent": False,
    }

    if key_path:
        try:
            connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(key_path)
        except Exception:
            connect_kwargs["key_filename"] = key_path

    if password:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)
    try:
        shell = client.invoke_shell()
        shell.settimeout(timeout)
        time.sleep(1)

        # Clear welcome banner
        if shell.recv_ready():
            shell.recv(65535)

        # Crucial for Cisco IOS: disable pagination to prevent --More-- stopping output
        shell.send("terminal length 0\n")
        time.sleep(0.8)
        if shell.recv_ready():
            shell.recv(65535)

        shell.send("show running-config\n")
        time.sleep(1.5)

        output = ""
        start_time = time.time()
        while True:
            if shell.recv_ready():
                chunk = shell.recv(65535).decode(errors="ignore")
                output += chunk
                lines = output.strip().splitlines()
                if lines and (lines[-1].endswith("#") or lines[-1].endswith(">")):
                    break
            else:
                time.sleep(0.5)

            # Safety timeout of 35 seconds per device
            if time.time() - start_time > 35:
                break

        return output
    finally:
        client.close()


def backup_device(device, driver="netmiko", key_path=None, password=None, timeout=20):
    """
    Dispatches backup to chosen driver.
    """
    if driver == "netmiko":
        return backup_device_netmiko(device, key_path=key_path, password=password, timeout=timeout)
    elif driver == "paramiko":
        return backup_device_paramiko(device, key_path=key_path, password=password, timeout=timeout)
    else:
        raise ValueError(f"Unknown driver: {driver}")


def save_backup(device_name, content, backup_dir=DEFAULT_BACKUP_DIR, with_timestamp=False):
    """
    Save backup content to a file in the backup directory.
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Primary filename: <device_name>_running-config.txt
    primary_filename = os.path.join(backup_dir, f"{device_name}_running-config.txt")
    with open(primary_filename, "w", encoding="utf-8") as f:
        f.write(content)

    if with_timestamp:
        ts_filename = os.path.join(backup_dir, f"{device_name}_running-config_{timestamp_str}.txt")
        with open(ts_filename, "w", encoding="utf-8") as f:
            f.write(content)
        return primary_filename, ts_filename

    return primary_filename, None


def run_backup(
    devices=None,
    driver="netmiko",
    key_path=None,
    password=None,
    backup_dir=DEFAULT_BACKUP_DIR,
    with_timestamp=False,
    host_override=None,
    timeout=20,
):
    """
    Execute backup for all target devices.
    """
    target_devices = devices or DEFAULT_DEVICES
    actual_key_path = resolve_ssh_key(key_path)

    print("=" * 60)
    print(" Network Devices Backup Automation")
    print("=" * 60)
    print(f"Driver      : {driver}")
    print(f"SSH Key     : {actual_key_path if actual_key_path else 'None (Password / Agent)'}")
    print(f"Backup Dir  : {os.path.abspath(backup_dir)}")
    print(f"Total Hosts : {len(target_devices)}")
    print("-" * 60)

    results = {"success": [], "failed": []}

    for dev in target_devices:
        device_copy = dict(dev)
        if host_override:
            device_copy["host"] = host_override

        name = device_copy["name"]
        host = device_copy["host"]
        port = device_copy["port"]

        print(f"[*] Backing up {name} ({host}:{port})...")
        try:
            config = backup_device(
                device_copy,
                driver=driver,
                key_path=actual_key_path,
                password=password,
                timeout=timeout,
            )

            primary_path, ts_path = save_backup(
                device_name=name,
                content=config,
                backup_dir=backup_dir,
                with_timestamp=with_timestamp,
            )

            size_bytes = len(config)
            print(f"[✓] {name}: Successfully backed up ({size_bytes} bytes) -> {primary_path}")
            if ts_path:
                print(f"    (Timestamped copy: {ts_path})")
            results["success"].append(name)

        except Exception as e:
            print(f"[✗] {name}: Backup failed - {e}")
            results["failed"].append((name, str(e)))

    print("-" * 60)
    print("Backup Summary:")
    print(f"  Success: {len(results['success'])} / {len(target_devices)}")
    if results["failed"]:
        print(f"  Failed : {len(results['failed'])}")
        for name, err in results["failed"]:
            print(f"    - {name}: {err}")
    print("=" * 60)

    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backup running-config for all network devices in the IPA project."
    )
    parser.add_argument(
        "--host",
        "-H",
        help=f"Override target host IP for all devices (default: {DEFAULT_HOST})",
        default=None,
    )
    parser.add_argument(
        "--driver",
        "-d",
        choices=["netmiko", "paramiko"],
        default="netmiko",
        help="SSH automation driver to use (default: netmiko)",
    )
    parser.add_argument(
        "--key",
        "-k",
        help="Path to SSH private key file (auto-detected if omitted)",
        default=None,
    )
    parser.add_argument(
        "--password",
        "-p",
        help="SSH password (optional, if key authentication is not used)",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=DEFAULT_BACKUP_DIR,
        help=f"Directory to save configuration files (default: {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "--timestamp",
        "-t",
        action="store_true",
        help="Keep an extra timestamped copy of each backup",
    )
    parser.add_argument(
        "--devices",
        help="Comma-separated list of device names to backup (e.g. R0-P,R1-P)",
        default=None,
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="SSH connection and command timeout in seconds (default: 20)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    selected_devices = DEFAULT_DEVICES
    if args.devices:
        names = [n.strip() for n in args.devices.split(",")]
        selected_devices = [d for d in DEFAULT_DEVICES if d["name"] in names]
        if not selected_devices:
            print(f"[!] Error: No matching devices found for filter: {args.devices}")
            sys.exit(1)

    run_backup(
        devices=selected_devices,
        driver=args.driver,
        key_path=args.key,
        password=args.password,
        backup_dir=args.output_dir,
        with_timestamp=args.timestamp,
        host_override=args.host,
        timeout=args.timeout,
    )
