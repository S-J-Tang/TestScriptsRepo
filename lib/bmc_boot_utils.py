import time
from datetime import datetime
import lib.ssh_util as ssh_util

DEFAULT_TIMEOUT_S = 60

def bmc_reboot(ssh):
    cmd = "shutdown -r now"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read(), stderr.read(), stdout.channel.recv_exit_status()

def wait_for_connection(target_info, status, await_time, logger=None):
    check_interval = 10
    start_time = datetime.now()

    while True:
        elapsed = datetime.now() - start_time
        if logger:
            logger.debug(f"Waiting for {status}, elapsed time: {elapsed}")

        if elapsed.total_seconds() >= int(await_time):
            if logger:
                logger.error("Timeout waiting for connection status")
            return False

        try:
            connected, ssh = ssh_util.get_ssh_session(target_info)
            if not connected:
                if status == "offline":
                    if logger:
                        logger.info("BMC is offline now")
                    return True
            else:
                stdin, stdout, stderr = ssh.exec_command("ls")
                rc = stdout.channel.recv_exit_status()
                if rc != 0 and status == "offline":
                    if logger:
                        logger.info("BMC is offline now")
                    return True
                if rc == 0 and status == "online":
                    return True
        except Exception:
            pass

        time.sleep(check_interval)

def wait_bmc_reboot_connection(target_info, timeout=600, interval=10):
    """
    Wait for BMC to go offline and then come back online.
    """

    def is_pingable(ip):
        import platform
        import subprocess
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        result = subprocess.run(['ping', param, '1', ip], stdout=subprocess.PIPE)
        return result.returncode == 0

    ip = target_info["ip"]
    start_time = datetime.now()

    print("[INFO] Waiting for BMC to go offline...")
    while (datetime.now() - start_time).total_seconds() < timeout:
        if not is_pingable(ip):
            print("[INFO] BMC is offline now.")
            break
        time.sleep(interval)
    else:
        print("[ERROR] Timeout: BMC never went offline.")
        return False

    print("[INFO] Waiting for BMC to come back online...")
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < timeout:
        if is_pingable(ip):
            print("[INFO] BMC is back online.")
            return True
        time.sleep(interval)

    print("[ERROR] Timeout: BMC did not come back online.")
    return False

def check_bmc_reboot(ip, logger):
    """Check if the BMC has rebooted successfully."""
    logger.info("Waiting for BMC to reboot and reconnect...")
    if not wait_bmc_reboot_connection({"ip": ip, "port": 22, "username": "root", "password": "0penBmc"}, timeout=600):
        logger.error(f"BMC failed to reconnect after reboot.")
        return False
    return True
