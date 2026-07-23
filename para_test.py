import paramiko
import time

print("Step 0: Script started", flush=True)

# ==== แก้ตรงนี้ให้ตรงกับ router ของคุณ ====
ip = "192.168.1.41"
username = "admin"
key_path = r"C:\Users\USER\Desktop\IPA_LAB\IPA_3\IPA\id_rsa"
# ==========================================

print("Step 1: Loading key...", flush=True)
private_key = paramiko.RSAKey.from_private_key_file(key_path)
print("Step 2: Key loaded, connecting...", flush=True)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.connect(
    hostname=ip,
    username=username,
    pkey=private_key,
    look_for_keys=False,
    allow_agent=False,
    timeout=10,
)
print("Step 3: Connected!", flush=True)

print("Step 4: Invoking shell...", flush=True)
shell = client.invoke_shell()
time.sleep(1)
if shell.recv_ready():
    shell.recv(65535)
print("Step 5: Shell ready", flush=True)

shell.send("terminal length 0\n")
time.sleep(1)
if shell.recv_ready():
    shell.recv(65535)
print("Step 6: Pagination disabled", flush=True)

shell.send("show running-config\n")
time.sleep(2)

output = ""
while shell.recv_ready():
    output += shell.recv(65535).decode()
    time.sleep(0.5)

print("Step 7: Output received", flush=True)
print("===== SHOW RUNNING-CONFIG =====")
print(output)

with open("R0_running-config.txt", "w") as f:
    f.write(output)

print("Step 8: Saved to file, closing connection", flush=True)
client.close()
print("Step 9: Done", flush=True)