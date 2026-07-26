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

R1_P_Config = [
    "show interfaces | include is up",
    "show version | include uptime",
]

R2_P_Config = [
    "show interfaces | include is up",
    "show version | include uptime",
]

def run_command(device, cmd):
    device_name = device.pop("name")
    conn_params = {**static, **device}

    print(f"Connecting to {device_name}...")
    conn = None
    try:
        conn = ConnectHandler(**conn_params)
        #.send_config_set ใช้ส่งชุดคำสั่งตั้งค่า
        # config_output = conn.send_config_set(cmd)
        # print(config_output)

        # ใช้ send_command แยกสำหรับคำสั่ง show (exec mode)
        for command in cmd:
            output = conn.send_command(command)
            print(output)

        print("done")
    except Exception as e:
        print(f"Error {device_name}: {e}")
    finally:
        if conn is not None:
            conn.disconnect()
        print(f"{device_name} done.\n")

if __name__ == "__main__":
    for device in device_list:
        # if device["name"] == "S1-P":
        #     run_command(device, S1_P_Config)
        if device["name"] == "R1-P":
            run_command(device, R1_P_Config)
        elif device["name"] == "R2-P":
                    run_command(device, R2_P_Config)