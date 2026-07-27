"""
test_textfsm.py

TDD test suite for textfsmlab.py.

textfsmlab.py uses exactly three libraries:
    - ntc-templates : parses "show cdp neighbors" (TextFSM)
    - Jinja2        : renders the interface/description config lines
    - Netmiko       : pulls CDP output from / pushes config to real devices

These tests exercise the pure parsing + templating logic only (no real
device needed). The Netmiko-facing functions (get_cdp_neighbors_raw,
push_interface_descriptions) talk to live hardware and are meant to be
run manually against your R1/R2/S1, not unit-tested here.

Replace the SAMPLE_CDP_* strings below with the REAL "show cdp neighbors"
output captured from your own R1, R2, and S1 (paste it exactly as the
device prints it). The fixtures here assume this topology, matching the
example on the lab slide:

    R1 G0/2  <---> G0/1 R2      (R1<->R2 link)
    R1 G0/0  <---> F0/1 S1      (R1<->S1 link)
    R1 G0/1  <---> PC           (no CDP neighbor -> manual override)
    R2 G0/3  <---> WAN (DHCP)   (no CDP neighbor -> manual override)

Run with:  pytest -v test_textfsm.py
"""

import pytest

from testfsm import (
    generate_config_lines,
    generate_descriptions,
    shorten_interface,
)

SAMPLE_CDP_R1 = """\
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
R2                Gig 0/2           178              R S I      CISCO2911  Gig 0/1
S1                Gig 0/0           165              S I        WS-C2960  Fas 0/1

Total cdp entries displayed : 2
"""

SAMPLE_CDP_R2 = """\
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
R1                Gig 0/1           178              R S I      CISCO2911  Gig 0/2

Total cdp entries displayed : 1
"""

SAMPLE_CDP_S1 = """\
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone,
                  D - Remote, C - CVTA, M - Two-port Mac Relay

Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
R1                Fas 0/1           165              R S I      CISCO2911  Gig 0/0

Total cdp entries displayed : 1
"""

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Gig 0/1", "G0/1"),
        ("GigabitEthernet0/2", "G0/2"),
        ("Gi0/3", "G0/3"),
        ("Fas 0/1", "F0/1"),
        ("FastEthernet0/2", "F0/2"),
    ],
)
def test_shorten_interface(raw, expected):
    assert shorten_interface(raw) == expected

def test_r1_link_to_r2():
    descriptions = generate_descriptions("R1", SAMPLE_CDP_R1)
    assert descriptions["G0/2"] == "Connect to G0/1 of R2"


def test_r1_link_to_s1():
    descriptions = generate_descriptions("R1", SAMPLE_CDP_R1)
    assert descriptions["G0/0"] == "Connect to F0/1 of S1"


def test_r1_pc_port_has_no_cdp_neighbor():
    descriptions = generate_descriptions("R1", SAMPLE_CDP_R1)
    assert descriptions["G0/1"] == "Connect to PC"

def test_r2_link_to_r1():
    descriptions = generate_descriptions("R2", SAMPLE_CDP_R2)
    assert descriptions["G0/1"] == "Connect to G0/2 of R1"


def test_r2_wan_dhcp_port():
    descriptions = generate_descriptions("R2", SAMPLE_CDP_R2)
    assert descriptions["G0/3"] == "Connect to WAN"

def test_s1_link_to_r1():
    descriptions = generate_descriptions("S1", SAMPLE_CDP_S1)
    assert descriptions["F0/1"] == "Connect to G0/0 of R1"

def test_config_lines_are_well_formed_pairs():
    lines = generate_config_lines("R1", SAMPLE_CDP_R1)
    assert len(lines) % 2 == 0
    for i in range(0, len(lines), 2):
        assert lines[i].startswith("interface ")
        assert lines[i + 1].startswith(" description ")


def test_config_lines_include_all_three_r1_ports():
    lines = generate_config_lines("R1", SAMPLE_CDP_R1)
    joined = "\n".join(lines)
    assert "interface G0/0" in joined
    assert "interface G0/1" in joined
    assert "interface G0/2" in joined