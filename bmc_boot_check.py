import time
import paramiko
import requests
import argparse
import socket

def is_bmc_pingable(ip, timeout=2):
    """Check if the BMC is pingable"""
    import platform
    import subprocess
    
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    try:
        response = subprocess.run(
            ['ping', param, '1', '-W', str(timeout), ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return response.returncode == 0
    except Exception as e:
        print(f"[ERROR] Ping failed: {e}")
        return False


def is_bmc_ssh_ready(ip, username='admin', password='admin', port=2200, timeout=5):
    """Check if the BMC is ready for SSH connection"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, port=port, username=username, password=password, timeout=timeout)
        client.close()
        return True
    except (paramiko.ssh_exception.NoValidConnectionsError, socket.timeout):
        return False
    except paramiko.AuthenticationException:
        print("[ERROR] SSH Authentication failed.")
        return False
    except Exception as e:
        print(f"[ERROR] SSH connection failed: {e}")
        return False


def is_bmc_redfish_ready(ip, timeout=5):
    """Check if the BMC Redfish API is available"""
    url = f"https://{ip}/redfish/v1"
    try:
        response = requests.get(url, verify=False, timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Redfish API check failed: {e}")
        return False

def wait_for_bmc_boot(ip, username='admin', password='admin', port=2200, max_wait=600, interval=10):
    """
    Wait for the BMC to complete booting
    - max_wait: Maximum wait time (seconds)
    - interval: Interval between checks (seconds)
    """
    start_time = time.time()
    while time.time() - start_time < max_wait:
        print(f"[INFO] Checking BMC status at {ip}...")

        if is_bmc_pingable(ip):
            print("[INFO] BMC is pingable.")
            return True  # All checks passed
        else:
            print("[WARNING] BMC is not pingable.")
            time.sleep(interval)
            continue
        
        # Uncomment if you want to check for SSH or Redfish readiness
        # if is_bmc_ssh_ready(ip, username, password, port=port):
        #     print("[INFO] BMC SSH is ready.")
        #     return True  # All checks passed
        # else:
        #     print("[WARNING] BMC SSH is not ready.")
        #     time.sleep(interval)
        #     continue

        # if is_bmc_redfish_ready(ip):
        #     print("[INFO] BMC Redfish API is ready.")
        #     return True  # All checks passed

        # print("[WARNING] BMC Redfish API is not ready. Retrying...")
        # time.sleep(interval)

    print("[ERROR] BMC did not boot up successfully within the given time.")
    return False

"""
Usage:
    python3 bmc_boot_check.py --ip 10.10.14.252 --username admin --password admin --max-wait 600 --interval 10
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wait for BMC to boot up after firmware update or AC reset.")
    parser.add_argument("--ip", default="10.10.14.229", help="BMC IP address")
    parser.add_argument("--username", default="root", help="SSH username (default: admin)")
    parser.add_argument("--password", default="0penBmc", help="SSH password (default: admin)")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 2200)")  # Added port parameter
    parser.add_argument("--max-wait", type=int, default=600, help="Maximum wait time in seconds (default: 600)")
    parser.add_argument("--interval", type=int, default=10, help="Interval between checks in seconds (default: 10)")
    args = parser.parse_args()

    if wait_for_bmc_boot(args.ip, args.username, args.password, args.port, args.max_wait, args.interval):
        print("[SUCCESS] BMC is up and ready!")
    else:
        print("[FAIL] BMC boot check failed!")
