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

def check_bmc_reboot(ip, logger):
    """Check if the BMC has rebooted successfully."""
    logger.info("Waiting for BMC to reboot and reconnect...")
    if not bbu.wait_bmc_reboot_connection({"ip": ip, "port": 22, "username": "root", "password": "0penBmc"}, timeout=600):
        logger.error(f"BMC failed to reconnect after reboot.")
        return False
    return True

def run_command(ssh, command, logger):
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()

    if error:
        logger.error(f"Error executing command: {command}")
        logger.error(error)
        return False  # Indicating a failure for this cycle
    else:
        logger.info(f"Command output: {output}")
    return True  # Success if no error is detected

def run_test_cycle(ip, cycle_num, logger):
    logger.info(f"Running test cycle {cycle_num}...")

    # Connect to BMC
    ssh = connect_bmc(ip, logger)

    # Step 1: MCTP link setup
    logger.info("Setting up MCTP link...")
    if not run_command(ssh, "mctp link", logger):  # If any command fails, return False
        logger.error(f"Error detected in MCTP setup during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)  # Wait for BMC to reboot
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    run_command(ssh, "mctp link set mctpi3c0 up", logger)
    run_command(ssh, "mctp addr", logger)
    run_command(ssh, "mctp addr add 8 dev mctpi3c0", logger)
    time.sleep(1)

    # Step 2: Busctl tree and busctl call
    logger.info("Displaying MCTP bus tree...")
    if not run_command(ssh, "busctl tree au.com.codeconstruct.MCTP1", logger):  # If any command fails, return False
        logger.error(f"Error detected in busctl during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False
    time.sleep(1)

    logger.info("Learning MCTP endpoint...")
    if not run_command(ssh, "busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x55", logger):  # If any command fails, return False
        logger.error(f"Error detected in learning MCTP endpoint during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False
    time.sleep(10)
    if not run_command(ssh, "busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x67", logger):  # If any command fails, return False
        logger.error(f"Error detected in learning MCTP endpoint during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    logger.info("Displaying MCTP bus tree...")
    if not run_command(ssh, "busctl tree au.com.codeconstruct.MCTP1", logger):  # If any command fails, return False
        logger.error(f"Error detected in busctl during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    # Step 3: Wait for 1 second
    logger.info("Sleeping for 1 second...")
    time.sleep(1)

    # Step 4: Execute PLDM tools
    logger.info("Getting TID using pldmtool...")
    if not run_command(ssh, "pldmtool base GetTID -m 30", logger):  # If any command fails, return False
        logger.error(f"Error detected in TID retrieval during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    logger.info("Getting Firmware parameters using pldmtool...")
    if not run_command(ssh, "pldmtool fw_update GetFwParams -m 30", logger):  # If any command fails, return False
        logger.error(f"Error detected in firmware parameter retrieval during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    logger.info("Getting TID using pldmtool...")
    if not run_command(ssh, "pldmtool base GetTID -m 20", logger):  # If any command fails, return False
        logger.error(f"Error detected in TID retrieval during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    logger.info("Getting Firmware parameters using pldmtool...")
    if not run_command(ssh, "pldmtool fw_update GetFwParams -m 20", logger):  # If any command fails, return False
        logger.error(f"Error detected in firmware parameter retrieval during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not check_bmc_reboot(ip, logger):
            return False
        return False

    # Reboot BMC at the end of the cycle
    ssh.exec_command("reboot")
    logger.info("Reboot command sent. BMC is restarting...")

    # Wait for BMC to reboot and reconnect
    time.sleep(5)
    if not check_bmc_reboot(ip, logger):
        logger.error(f"BMC reboot check failed in cycle {cycle_num}.")
        return False  # Cycle failed

    # Close the SSH session
    ssh.close()
    return True  # Cycle passed

def main(ip):
    # Initialize logger
    logger = init_logger("MMC_FW_update_stress.log", verbose=True)

    # Track the number of failed cycles
    failure_count = 0

    # Run 10 test cycles
    for cycle_num in range(1, 11):
        success = run_test_cycle(ip, cycle_num, logger)
        if not success:
            failure_count += 1  # Increment failure count if test fails
            logger.error(f"Test cycle {cycle_num} failed. Continuing with next cycle.")
        time.sleep(2)  # Delay between cycles to avoid continuous strain

    # Calculate fail rate
    total_cycles = 10
    fail_rate = (failure_count / total_cycles) * 100

    # Log fail rate
    logger.info(f"Fail rate: {fail_rate}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.14.229")
    args = parser.parse_args()
    main(args.ip)
