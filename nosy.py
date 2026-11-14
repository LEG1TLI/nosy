from ast import arg
from http.server import SimpleHTTPRequestHandler
import os 
import signal
import subprocess
import sys

from blinker import signal
import pyfiglet
import shlex
import mimetypes
import glob
import re
import shutil
#mount point and device path. change as needed. This is set to the default device paths for raspberry pi 
mount_point = "/mnt/usb_check"
dev_path = "/dev/sda1"
usb = "/sys/bus/usb/devices"
allowed_filesystems = {"vfat", "exfat", "ntfs3", "ntfs", "iso9660", "udf", "ext4", "ext3", "ext2"}
args = ["bwrap", "--unshare-all", "--share-net", "--sie-with-parent", "--new-session", "--cap-drop", "ALL"]
for d in ("/usr", "/lib", "/lib64", "/bin", "/sbin"):
    if os.path.islink(d): args += ["--symlink", os.readlink(d), d]
    elif os.path.isdir(d): args += ["--ro-bind", d, d]
args += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
         "--ro-bind", os.path.abspath(__file__), "/app/nosy.py",
         sys.executable, "/app/nosy.py", "--serve-child", "/srv", port]]

def clean(s):
    return re.sub(r"[\x00-\x1f\x7f-\x95]", "?", s)

signal.signal(signal.SIGHUP, lambda *_: sys.exit(1))
signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))
class safe_handler(SimpleHTTPRequestHandler):
    root = None
    def _ok(self):
        p = os.path.realpath(self.translate_path(self.path))
        if not (p == self.root or p.startswith(self.root + os.sep)):
            return False
        return not os.path.exists(p) or os.path.isdir(p) or os.stat.S_ISREG(os.stat(p).st_mode)
    def do_GET(self):
        self.send_error(403) if not self._ok() else super().do_GET()
    def do_HEAD(self):
        self.send_error(403) if not self._ok() else super().do_HEAD()
    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXT_EXCEPT_SVG: return mimetypes.types_map[ext]
        if ext in TEXT_EXT: return "text/plain; charset=utf-8"
        return "application/octet-stream"
    def end_headers(self):
        self.send_header("Content-Security-Policy", "sandbox; default-src 'none'; img-src 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()



def print_banner():
    banner = pyfiglet.figlet_format("NOSY", font="slant")
    print(banner)

print_banner()

def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, text =True, **kw)

def hardened_moutn(dev, mount_point):
    fs = run(["blkid", "-o", "value", "-s", "TYPE", dev]).stdout.strip()
    supported = open("/proc/filesystems").read()
    if fs not in allowed_filesystems or fs not in supported:
        print("filesystem not supported.")
        return False
    opts = "ro,noexec,nosuid,nodev,noatime" + (",noload" if fs.startwith("ext") else "")
    return as_root(["mount", "-t", fs, "-o", opts, "--", dev, mount_point]).returncode == 0

def lock_usb():
    saved = {}
    for hub in glob.glog(f"{usb}/usb*"):
        f = f"{hub}/authorized_default"
        if not os.path.exists(f):
            continue
    saved[f] = open(f).read().strip()
    #using 2 will only authorize the hardwired internal devices so u can fall back to 0 on older kernels 
    if as_root(["tee", f], input="2").returncode != 0:
        as_root(["tee", f], input="0")
    return saved

def as_root(cmd, **kw):
    prefix = [] if os.getuid() == 0 else [shutil.which("sudo") or shutil.which("doas")]
    return run(prefix + shlex.split(cmd), **kw)

#defining for device nodes like 1-1.2 and that kinda thing.
def usb_devices(): 
    return {p for p in os.listdir(usb) if re.fullmatch(r"\d+-[\d.]+", p)}

def interface_classes(dev):
    d = open(f"{usb}/{dev}/descriptors", "rb").read()
    i, out = 0, []
    while i + 2 <= len(d) and d[i]:
        if d[i + 1] == 4 and i + 6 <= len(d):   #descriptor for the interface
            out.append(d[i = 5])
        i += d[i]
    return out 

def prompt(msg, default = "n"):
    choice = input(msg).strip().lower()
    if not choice:
        choice = default.lower()
    return choice in ("y", "yes")

def inspect_usb():
    print(f"[*] Pre-mount device check for {dev_path}")

    if not os.path.exists(dev_path):
        print(f"[!] Device at {dev_path} not found. Are you sure the device is connected?")
        return False

    checks = [
        f"lsblk {shlex.quote(dev_path)}",
        f"blkid {shlex.quote(dev_path)}",
        f"file -s {shlex.quote(dev_path)}"
    ]

    all_ok = True
    for cmd in checks:
        print(f"\n$ {cmd}")
        result = run(cmd)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(f"[!] Error: {result.stderr.strip()}")
        if result.returncode != 0:
            all_ok = False

    return all_ok

def mount_usb():
    #mount the usb drive as read only and create directory if it isn't there
    if not os.path.exists(mount_point):
        os.makedirs(mount_point, exist_ok=True)

    if os.path.ismount(mount_point):
        print(f"[!] {mount_point} is already mounted.")
        return True
    
    print(f"[*] Attempting to mount {dev_path} as Read-Only.")
    result = run_cmd(f"sudo mount -o ro,noexec,nosuid {shlex.quote(dev_path)} {shlex.quote(mount_point)}")
    if result.returncode == 0:
        print("[+] Mount successful.")
        return True
    else:
        print(f"[!] Failed to mount {dev_path}. Error: {result.stderr.strip()}")
        return False
def unmount_usb():
    if os.path.ismount(mount_point):
        print(f"[*] Unmounting {mount_point}...")
        result = run_cmd(f"sudo umount {shlex.quote(mount_point)}")
        if result.returncode == 0:
            print("[+] Successfully unmounted. The drive is now safe to remove.")
        else:
            print(f"[!] Failed to unmount drive. Error: {result.stderr.strip()}")

def scan_drive():
    all_files = []
    for root, _, files in os.walk(mount_point):
        for file_name in files:
            all_files.append(os.path.join(root, file_name))
    return sorted(all_files)

def is_image(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")

def is_text(path):
    mime, _ = mimetypes.guess_type(path)
    if mime and mime.startswith("text"):
        return True
    
    result = run_cmd(f"file -b --mime-type {shlex.quote(path)}")
    return result.stdout.strip().startswith("text/")

def read_text_file(path, max_lines=200):
    print(f"\n[+] Reading text file: {path}")
    try:
        with open(path, "r", encoding = "utf-8", errors = "replace") as f:
            for i, line in enumerate(f, start=1):
                if i > max_lines:
                    print(f"\n[...output truncated after {max_lines} lines...]")
                    break
                print(line.rstrip("\n"))
    except Exception as e:
        print(f"[!] Could not read file: {e}")
    print("End.")

def browse_terminal(file_list):
    if not file_list:
        print("[-] No files found on mounted device")
        return
    
    while True:
        #show amount of files found and their index, type and path
        print(f"\n[*] Found {len(file_list)} Files:")
        for idx, path in enumerate(file_list):
            kind = "OTHER"
            if is_image(path):
                kind = "IMAGE"
            elif is_text(path):
                kind = "TEXT"
            print(f"[{idx}] ({kind}) {path}")

        choice = input("\nEnter file index to open, r to rescan, or q to return: ").strip().lower()
        if choice == "q":
            return
        elif choice == "r":
            file_list[:] = scan_drive()
            continue
        if not choice.isdigit():
            print("[!] Invalid selection.")
            continue

        idx = int(choice)
        if idx < 0 or idx >= len(file_list):
            print("[!] Index out of range.")
            continue

        selected = file_list[idx]
        if is_image(selected) and shutil.which("timg"):
            subprocess.run(["timg", "-g100x100", selected])
        elif is_text(selected):
            read_text_file(selected)
        else:
            result = run_cmd(f"file -b {shlex.quote(selected)}")
            print(f"[-] Non-image/text file: {selected}")
            if result.stdout.strip():
                print(f"    Type: {result.stdout.strip()}")
#start web server for easy viewing of files in browser
#TODO: create fancy web interface for viewing files.
def start_web_server():
    port_raw = input("Port for HTTP server (default 8000): ").strip()
    port = port_raw if port_raw else "8000"

    if not port.isdigit():
        print("[!] Invalid port")
        return
    
    print(f"[*] Starting HTTP server on 0.0.0.0:{port}, serving {mount_point}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", port, "--directory", mount_point]
    )
    print(f"[+] Open in browser: http://<PI_IP>:{port}")
    print("[*] Press Enter to stop the web server...")
    input()

    proc.terminate()
    proc.wait()
    print("[+] Web server stopped.")

def mounted_menu():
    files = scan_drive()

    while True:
        print("\n[*] Mounted Drive Menu:")
        print("[1] Browse files in terminal")
        print("[2] Start HTTP web server")
        print("[3] Unmount drive and exit")
        print("[4] Rescan drive for new files")

        choice = input("Select an option: ").strip()
        if choice == "1":
            browse_terminal(files)
        elif choice == "2":
            start_web_server()
        elif choice == "3":
            unmount_usb()
            return
        elif choice == "4":
            files[:] = scan_drive()
            print("[*] Rescan complete.")
        else:
            print("[!] Invalid selection.")

def main():
    print("[*] Starting NOSY - Non-executing Observer for Storage Yields")

    if not inspect_usb():
        return
    
    if not prompt("\n[*] Do you want to mount the drive as read-only? (y/n) ", default="y"):
        print("[*] Exiting without mounting.")
        return
    
    if mount_usb():
        try:
            mounted_menu()
        finally:
            if os.path.ismount(mount_point):
                unmount_usb()

if __name__ == "__main__":
    main()