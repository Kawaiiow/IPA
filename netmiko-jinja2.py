from netmiko import ConnectHandler
from jinja2 import Environment, BaseLoader

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
}

# Jinja2: ใช้ .render() แปลง template (string) ให้เป็น config จริง
env = Environment(loader=BaseLoader())

S1_P_Config = env.from_string("""
vlan {{ vlan_id }}
name {{ vlan_name }}
exit

interface range GigabitEthernet0/1-2
switchport access vlan {{ vlan_id }}
exit

do wr
""").render(
    vlan_id=101,
    vlan_name="Control-Data",
).splitlines()
S1_P_Config = [line for line in S1_P_Config if line.strip() != ""]


R1_P_Config = env.from_string("""
int loopback 1
ip vrf forwarding {{ vrf_name }}
ip address {{ r1_loopback_ip }} 255.255.255.255
exit
router ospf 1 vrf {{ vrf_name }}
network 172.31.49.0 0.0.0.15 area 0
network 172.31.49.32 0.0.0.15 area 0
network 172.31.49.16 0.0.0.3 area 0
network {{ r1_loopback_ip }} 0.0.0.0 area 0

do wr
""").render(
    vrf_name="Control-Data",
    r1_loopback_ip="1.1.1.1",
).splitlines()
R1_P_Config = [line for line in R1_P_Config if line.strip() != ""]


R2_P_Config = env.from_string("""
int loopback 1
ip vrf forwarding {{ vrf_name }}
ip address {{ r2_loopback_ip }} 255.255.255.255
exit

router ospf 1 vrf {{ vrf_name }}
network 172.31.49.0 0.0.0.15 area 0
network 172.31.49.16 0.0.0.3 area 0
network {{ r2_loopback_ip }} 0.0.0.0 area 0
default-information originate
exit

int range g0/1-2
ip nat inside
exit

int g0/3
ip nat outside
exit

ip route vrf {{ vrf_name }} 0.0.0.0 0.0.0.0 {{ nat_next_hop }} global
access-list 1 permit 172.31.49.0 0.0.0.255
ip nat inside source list 1 interface GigabitEthernet0/3 vrf {{ vrf_name }} overload
ip dns server
ip domain-lookup
ip name-server 8.8.8.8

access-list 101 deny tcp host 172.31.49.11 host 172.31.49.9 eq 22
access-list 101 deny tcp host 172.31.49.11 host 172.31.49.9 eq 23
access-list 101 deny tcp host 172.31.49.11 172.31.49.16 0.0.0.3 eq 22
access-list 101 deny tcp host 172.31.49.11 172.31.49.16 0.0.0.3 eq 23
access-list 101 deny tcp host 172.31.49.11 172.31.49.32 0.0.0.15 eq 22
access-list 101 deny tcp host 172.31.49.11 172.31.49.32 0.0.0.15 eq 23
access-list 101 permit ip any any

int g0/2
ip access-group 101 in
exit

do wr
""").render(
    vrf_name="Control-Data",
    r2_loopback_ip="2.2.2.2",
    nat_next_hop="192.168.42.1",  # Warning NAT IP Changed
).splitlines()
R2_P_Config = [line for line in R2_P_Config if line.strip() != ""]


def run_command(device, cmd):
    device_name = device.pop("name")
    conn_params = {**static, **device}

    print(f"Connecting to {device_name}...")
    conn = None
    try:
        conn = ConnectHandler(**conn_params)
        #.send_config_set ใช้ส่งชุดคำสั่งตั้งค่า
        config_output = conn.send_config_set(cmd)
        print(config_output)

        # ใช้ send_command แยกสำหรับคำสั่ง show (exec mode)
        # show_output = conn.send_command("show vlan brief")
        # print(show_output)

        print("done")
    except Exception as e:
        print(f"Error {device_name}: {e}")
    finally:
        if conn is not None:
            conn.disconnect()
        print(f"{device_name} done.\n")


if __name__ == "__main__":
    for device in device_list:
        if device["name"] == "S1-P":
            run_command(device, S1_P_Config)
        elif device["name"] == "R1-P":
            run_command(device, R1_P_Config)
        elif device["name"] == "R2-P":
            run_command(device, R2_P_Config)