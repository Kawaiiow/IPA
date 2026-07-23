import paramiko
import time
# Key
key_path = r"C:\Users\USER\Desktop\IPA_LAB\IPA_3\IPA\id_rsa"
# Device List
devices = [
    # host ip can change depend on Router
    {"name": "R0-P", "host": "192.168.1.41", "port": 22, "username": "admin"},
    {"name": "R1-P", "host": "192.168.1.41", "port": 2222, "username": "admin"},
    {"name": "R2-P", "host": "192.168.1.41", "port": 2223, "username": "admin"},
    {"name": "S0-P", "host": "192.168.1.41", "port": 2224, "username": "admin"},
    {"name": "S1-P", "host": "192.168.1.41", "port": 2225, "username": "admin"},
]

private_key = paramiko.RSAKey.from_private_key_file(key_path)

def backup_device(device):
    name = device["name"]
    ip = device["host"]
    port = device["port"]
    username = device["username"]

    try:
        print("Connect")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=ip,
            port=port,
            username=username,
            pkey=private_key,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        #Create Shell
        print("Create Shell")
        shell = client.invoke_shell()
        time.sleep(1)
        if shell.recv_ready():
            shell.recv(65535)
        #do sh run
        if name == "R0-P":
            print("do show run")
            shell.send("sh run\n")
            time.sleep(2)

            print("waiting.....")
            output = ""
            while shell.recv_ready():
                output += shell.recv(65535).decode(errors="ignore")
                time.sleep(0.5)

            filename = name + "_running-config.txt"
            with open(filename, "w") as f:
                f.write(output)
            print(f"Back up {name} Done Next")
            client.close()
        else:
            print(f"Connect {name} Done Next")
            client.close()

    except:
        print(f"Error", flush=True)

for dev in devices:
    backup_device(dev)
