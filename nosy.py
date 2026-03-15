import os 
import subprocess
import sys

mount_point = "/mnt/usb_check"
dev_path = "/dev/sda1"

def run_cmd(cmd):
    #Allows to run shell commands and capture output
    return subprocess.run(cmd, shell = True, capture_output = True, text = True)

def mount_usb():
    if not os.path.exists(mount_point):
        os.mkdirs(mount_point)

    if os.path.ismount(mount_point):
        print(f"[!] {mount_point} is already mounted.")
        return True
    
    print(f"[*] Attempting to mount {dev_path} as Read-Only.")
    result = run_cmd(f"sudo mount -o ro,noexec,nosuid {dev_path} {mount_point}")
    if result.returncode == 0:
        print("[+] Mount successful.")
        return True
    else:
        print(f"[!] Failed to mount {dev_path}. Error: {result.stderr.strip()}")
        return False
def browse_images():
    extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')
    images = []

    for root, dirs, files in os.walk(mount_point):
        for file in files:
            if files.lower.endswith(extensions):
                images.append(os.path.join(root, file))
    if not images:
        print("[-] No images located on drive.")
        return
    
    print(f"[-] Found {len(images)} images.")