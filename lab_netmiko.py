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
    "network 1.1.1.1 0.0.0.0 area 0",
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
# if __name__ == "__main__":
#     for device in device_list:
#         run_command(device, "show ip interface brief")






# if __name__ == "__main__":
#     run_command("R0-P","sh ip int br")