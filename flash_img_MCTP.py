import argparse
import sys
import time
import lib.ssh_util as ssh_util
import lib.bmc_boot_utils as bbu
from lib.init_logger import init_logger

def run_test_cycle(ip, cycle_num, logger):
    logger.info(f"Running test cycle {cycle_num}...")

    # Connect to BMC
    ssh = ssh_util.connect_bmc(ip, logger)

    # Step 1: MCTP link setup
    logger.info("Setting up MCTP link...")
    if not ssh_util.run_command(ssh, "mctp link", logger):  # If any command fails, return False
        logger.error(f"Error detected in MCTP setup during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)  # Wait for BMC to reboot
        if not bbu.check_bmc_reboot(ip, logger):
            return False
        return False

    ssh_util.run_command(ssh, "mctp link set mctpi3c0 up", logger)
    ssh_util.run_command(ssh, "mctp addr", logger)
    ssh_util.run_command(ssh, "mctp addr add 8 dev mctpi3c0", logger)
    time.sleep(1)

    # Step 2: Busctl tree and busctl call
    logger.info("Displaying MCTP bus tree...")
    if not ssh_util.run_command(ssh, "busctl tree au.com.codeconstruct.MCTP1", logger):  # If any command fails, return False
        logger.error(f"Error detected in busctl during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not bbu.check_bmc_reboot(ip, logger):
            return False
        return False
    time.sleep(1)

    logger.info("Learning MCTP endpoint...")
    if not ssh_util.run_command(ssh, "busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x1E", logger):  # If any command fails, return False
        logger.error(f"Error detected in learning MCTP endpoint during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not bbu.check_bmc_reboot(ip, logger):
            return False
        return False

    logger.info("Displaying MCTP bus tree...")
    if not ssh_util.run_command(ssh, "busctl tree au.com.codeconstruct.MCTP1", logger):  # If any command fails, return False
        logger.error(f"Error detected in busctl during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not bbu.check_bmc_reboot(ip, logger):
            return False
        return False

    # Step 3: Wait for 1 second
    logger.info("Sleeping for 1 second...")
    time.sleep(1)

    # Step 4: Execute PLDM tools
    logger.info("Getting TID using pldmtool...")
    if not ssh_util.run_command(ssh, "pldmtool base GetTID -m 30", logger):  # If any command fails, return False
        logger.error(f"Error detected in TID retrieval during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not bbu.check_bmc_reboot(ip, logger):
            return False
        return False

    logger.info("Getting Firmware parameters using pldmtool...")
    if not ssh_util.run_command(ssh, "pldmtool fw_update GetFwParams -m 30", logger):  # If any command fails, return False
        logger.error(f"Error detected in firmware parameter retrieval during cycle {cycle_num}. Rebooting BMC...")
        ssh.exec_command("reboot")
        time.sleep(5)
        if not bbu.check_bmc_reboot(ip, logger):
            return False
        return False

    # Step 5: Uploading image file
    logger.info("Uploading image file to BMC...")
    img_path = "/home/billy/Desktop/meta/sitv3/sit/img/SB_SI_29.pldm"  # Example path, update with your actual file
    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }
    if not ssh_util.push_file(target, img_path, remote_dir="/tmp"):
        logger.error(f"Failed to upload {img_path} to BMC.")
        return False
    
    # Step 6: Move file from /tmp to /tmp/pldm_images on the BMC
    logger.info(f"Copying file from /tmp to /tmp/pldm_images on BMC...")
    copy_command = "cp /tmp/SB_SI_29.pldm /tmp/pldm_images/"
    if not ssh_util.run_command(ssh, copy_command, logger):
        logger.error(f"Failed to copy file from /tmp to /tmp/pldm_images on BMC.")
        return False


    # Close the SSH session
    ssh.close()
    return True  # Cycle passed

def main(ip):
    # Initialize logger
    logger = init_logger("MMC_FW_update_stress.log", verbose=True)

    # Track the number of failed cycles
    failure_count = 0
    total_cycles = 1

    # Run 10 test cycles
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
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.14.229")
    args = parser.parse_args()
    main(args.ip)
