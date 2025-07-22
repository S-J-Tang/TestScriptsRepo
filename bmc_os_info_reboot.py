import paramiko
import argparse
import sys
import time
import lib.ssh_util as ssh_util
import lib.bmc_boot_utils as bbu
from lib.init_logger import init_logger

def connect_bmc(ip, logger):
    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }

    # Establish SSH connection
    connected, ssh = ssh_util.get_ssh_session(target)
    if not connected:
        logger.error(f"Failed to connect to BMC at {ip}")
        sys.exit(1)

    logger.info(f"Connected to {ip}")
    return ssh

def main(ip):
    # Initialize logger
    logger = init_logger("bmc_reboot.log", verbose=True)

    # Connect to BMC
    ssh = connect_bmc(ip, logger)

    # Display OS information
    logger.info("Reading /etc/os-release...")
    stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release")
    logger.info(stdout.read().decode())

    # Reboot BMC
    ssh.exec_command("reboot")
    logger.info("Reboot command sent. BMC is restarting...")

    # Wait for BMC to reboot and reconnect
    time.sleep(5)
    if not bbu.wait_bmc_reboot_connection({"ip": ip, "port": 22, "username": "root", "password": "0penBmc"}, timeout=600):
        logger.error("BMC reboot check failed.")
        sys.exit(1)

    # Reconnect to BMC after reboot
    ssh = connect_bmc(ip, logger)

    # Read OS information again
    logger.info("Reading /etc/os-release...")
    stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release")
    logger.info(stdout.read().decode())

    ssh.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="Target BMC IP address", default="10.10.14.229")  # Default IP set here
    args = parser.parse_args()
    main(args.ip)
