import re
import time

from jinja2 import Environment
from netmiko import ConnectHandler
from ntc_templates.parse import parse_output


def parse_cdp_neighbors(raw_output):
    rows = parse_output(
        platform="cisco_ios",
        command="show cdp neighbors",
        data=raw_output,
    )
    return [_fix_platform_swallow(r) for r in rows]


def _fix_platform_swallow(row):
    # ntc-templates' PLATFORM regex can greedily eat the interface-type
    # letters off the front of neighbor_interface (space-separated or
    # glued directly onto platform, e.g. "CISCO2911 Gig" / "CISCO2911Gig"
    # instead of "CISCO2911"), leaving neighbor_interface as just "0/2".
    # Move those letters back if that happened.
    platform = row.get("platform", "")
    neighbor_intf = row.get("neighbor_interface", "")
    if not neighbor_intf or not neighbor_intf[0].isdigit():
        return row

    match = re.match(r"^(.*?)([A-Za-z]{2,4})$", platform)
    if not match:
        return row
    head, tail = match.group(1).rstrip(), match.group(2)
    if head and any(name.startswith(tail.lower()) for name in INTERFACE_ABBR):
        row["platform"] = head
        row["neighbor_interface"] = f"{tail} {neighbor_intf}"
    return row


INTERFACE_ABBR = {
    "gigabitethernet": "G",
    "tengigabitethernet": "Te",
    "fastethernet": "F",
    "ethernet": "Et",
    "serial": "S",
    "loopback": "Lo",
    "vlan": "Vl",
    "port-channel": "Po",
}


def shorten_interface(raw):
    compact = raw.replace(" ", "")
    match = re.match(r"^([A-Za-z\-]+)([\d/.]+)$", compact)
    if not match:
        return compact
    prefix, rest = match.groups()
    prefix_l = prefix.lower()
    for long_name, short in INTERFACE_ABBR.items():
        if long_name.startswith(prefix_l):
            return f"{short}{rest}"
    return compact


def clean_neighbor_name(name):
    return name.split(".")[0]


def build_description(neighbor_name, neighbor_interface):
    device = clean_neighbor_name(neighbor_name)
    return f"Connect to {shorten_interface(neighbor_interface)} of {device}"


PC_INTERFACES = {
    ("R1", "G0/1"),
    ("S1", "G0/2"),
}

WAN_DHCP_INTERFACES = {
    ("R2", "G0/3"),
}

IGNORE_NEIGHBORS = {"S0-P"}


def generate_descriptions(device, raw_cdp_output):
    descriptions = {}

    for dev, intf in PC_INTERFACES:
        if dev == device:
            descriptions[intf] = "Connect to PC"

    for dev, intf in WAN_DHCP_INTERFACES:
        if dev == device:
            descriptions[intf] = "Connect to WAN"

    for n in parse_cdp_neighbors(raw_cdp_output):
        local_intf = shorten_interface(n["local_interface"])
        if local_intf in descriptions:
            continue

        neighbor_name = clean_neighbor_name(n["neighbor_name"])
        if neighbor_name in IGNORE_NEIGHBORS:
            continue

        neighbor_intf = shorten_interface(n["neighbor_interface"])
        if neighbor_intf[:1].isdigit():
            local_prefix = re.match(r"^[A-Za-z]+", local_intf)
            if local_prefix:
                neighbor_intf = f"{local_prefix.group(0)}{neighbor_intf}"

        descriptions[local_intf] = f"Connect to {neighbor_intf} of {neighbor_name}"

    return descriptions


_jinja_env = Environment(trim_blocks=True, lstrip_blocks=True)

CONFIG_TEMPLATE = _jinja_env.from_string(
    "{% for intf, desc in interfaces.items() %}"
    "interface {{ intf }}\n"
    " description {{ desc }}\n"
    "{% endfor %}"
)


def generate_config_lines(device, raw_cdp_output):
    descriptions = generate_descriptions(device, raw_cdp_output)
    rendered = CONFIG_TEMPLATE.render(interfaces=descriptions)
    return [line for line in rendered.splitlines() if line]


device_list = [
    {"name": "R0-P", "host": "192.168.1.41", "port": 22},
    {"name": "R1-P", "host": "192.168.1.41", "port": 2222},
    {"name": "R2-P", "host": "192.168.1.41", "port": 2223},
    {"name": "S0-P", "host": "192.168.1.41", "port": 2224},
    {"name": "S1-P", "host": "192.168.1.41", "port": 2225},
]

static = {
    "device_type": "cisco_ios",
    "username": "admin",
    "use_keys": True,
    "key_file": r"C:\Users\USER\Desktop\IPA_LAB\IPA_3\IPA\id_rsa",
    "disable_sha2_fix": True,
    "conn_timeout": 20,
    "banner_timeout": 20,
    "auth_timeout": 20,
    "fast_cli": False,
    "global_delay_factor": 2,
}

TARGET_DEVICES = ["R1-P", "R2-P", "S1-P"]


def configure_descriptions(device, retries=2):
    device = dict(device)
    device_name = device.pop("name")
    logical_name = device_name.replace("-P", "")
    conn_params = {**static, **device}

    print(f"Connecting to {device_name}...")

    for attempt in range(1, retries + 2):  # e.g. retries=2 -> up to 3 tries
        conn = None
        try:
            conn = ConnectHandler(**conn_params)

            raw_cdp = conn.send_command("show cdp neighbors", read_timeout=30)
            config_lines = generate_config_lines(logical_name, raw_cdp)

            config_output = conn.send_config_set(config_lines)
            print(config_output)

            conn.save_config()
            print("done")
            break  # success, stop retrying
        except Exception as e:
            print(f"Error {device_name} (attempt {attempt}): {e}")
            if attempt <= retries:
                print(f"Retrying {device_name}...")
                time.sleep(3)
        finally:
            if conn is not None:
                conn.disconnect()

    print(f"{device_name} done.\n")


if __name__ == "__main__":
    for device in device_list:
        if device["name"] in TARGET_DEVICES:
            configure_descriptions(device)