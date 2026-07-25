from netmiko import ConnectHandler

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

S1_P_Config =[
    "vlan 101",
    "name Control-Data",
    "exit",

    "interface range GigabitEthernet0/1-2",
    "switchport access vlan 101",
    "exit",
]

R1_P_Config = [
    "int loopback 1",
    "ip vrf forwarding Control-Data",
    "ip address 1.1.1.1 255.255.255.255",
    "exit",
    "router ospf 1 vrf Control-Data",
    "network 172.31.49.0 0.0.0.15 area 0",
    "network 172.31.49.16 0.0.0.3 area 0",
    "network 1.1.1.1 0.0.0.0 area 0",

    # "access-list 101 deny tcp host 172.31.49.10 host 172.31.49.6",
    # "access-list 101 deny tcp host 172.31.49.10 host 172.31.49.6"

]

R2_P_Config = [
    "int loopback 1",
    "ip vrf forwarding Control-Data",
    "ip address 2.2.2.2 255.255.255.255",
    "exit",

    "router ospf 1 vrf Control-Data",
    "network 172.31.49.0 0.0.0.15 area 0",
    "network 172.31.49.16 0.0.0.3 area 0",
    "network 2.2.2.2 0.0.0.0 area 0",
    "default-information originate", #Advise Default Route to ospf
    "exit",

    # "ip route 0.0.0.0 0.0.0.0 GigabitEthernet0/3",
    "int range g0/1-2",
    "ip nat inside",
    "exit",

    "int g0/3",
    "ip nat outside",
    "exit",

    "ip route vrf Control-Data 0.0.0.0 0.0.0.0 192.168.42.1 global",
    "access-list 1 permit 172.31.49.0 0.0.0.255",
    "ip nat inside source list 1 interface GigabitEthernet0/3 vrf Control-Data overload",
    "ip dns-server",
    "ip domain-lookup",
    "ip name-server 8.8.8.8",
]

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
# if __name__ == "__main__":
#     for device in device_list:
#         run_command(device, "show ip interface brief")






# if __name__ == "__main__":
#     run_command("R0-P","sh ip int br")