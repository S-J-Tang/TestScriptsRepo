import lib.ssh_util
import time
import lib.bmc_boot_utils as bbu
import argparse
import sys

def main(ip):
    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }

    connected, ssh = lib.ssh_util.get_ssh_session(target)
    if not connected:
        print(f"Failed to connect to BMC")
        sys.exit(1)

    print(f"Connected")

    _, stdout, _ = ssh.exec_command("mfg-tool power-control -p 0 -s standby -a cycle")
    output = stdout.read().decode()
    print(output)

    time.sleep(10)
    if not bbu.wait_bmc_reboot_connection(target, timeout=600):
        print("BMC reboot failed.")
        sys.exit(1)
    print("BMC reboot success.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.14.94")  # Default IP set here
    args = parser.parse_args()
    main(args.ip)