import paramiko
import argparse
import sys
import time
import lib.ssh_util as ssh_util
import lib.bmc_boot_utils as bbu
from lib.init_logger import init_logger
import lib.bmc_util as bu

def run_test_cycle(ip, cycle_num, logger):
    logger.info(f"Running test cycle {cycle_num}...")

    # Connect to BMC
    ssh = ssh_util.connect_bmc(ip, logger)

    # Display usb port
    logger.info("Reading /etc/os-release...")
    stdin, stdout, stderr = ssh.exec_command("lsusb -vt")
    logger.info(stdout.read().decode())

    # Display mmc platform info
    logger.info("Reading mmc platform info...")
    mmc = bu.SerialSSHClient(ssh, "ttyUSB5", logger)
    logger.info(mmc.send_command("platform info"))
    mmc.close()
    ssh.close()
    return True  # Cycle passed

def main(ip):
    # Initialize logger
    logger = init_logger("bmc_reboot.log", verbose=True)
    total_cycles = 1
    failure_count = 0

    # Run 1 test cycles
    for cycle_num in range(1, total_cycles+1):
        success = run_test_cycle(ip, cycle_num, logger)
        if not success:
            failure_count += 1  # Increment failure count if test fails
            logger.error(f"Test cycle {cycle_num} failed. Continuing with next cycle.")
        time.sleep(2)  # Delay between cycles to avoid continuous strain

    fail_rate = (failure_count / total_cycles) * 100

    # Log fail rate
    logger.info(f"Fail rate: {fail_rate}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.15.221")  # Default IP set here
    args = parser.parse_args()
    main(args.ip)
