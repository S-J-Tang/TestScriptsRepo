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

    # Step 1: Hotjoin command for I3C bus
    logger.info("Hotjoining I3C bus...")
    if not ssh_util.run_command(ssh, "echo 1 > /sys/bus/i3c/devices/i3c-0/hotjoin", logger):
        logger.error("Failed to hotjoin I3C bus.")
        return False

    # Step 2: I2C set command
    logger.info("Setting I2C device...")
    if not ssh_util.run_command(ssh, "i2cset -y 10 0x21 0x40", logger):
        logger.error("Failed to set I2C device.")
        return False
    time.sleep(1)

    # Step 3: MCTP link setup
    logger.info("Setting up MCTP link...")
    if not ssh_util.run_command(ssh, "mctp link", logger):
        logger.error("Failed to setup MCTP link.")
        return False

    if not ssh_util.run_command(ssh, "mctp link set mctpi3c0 up", logger):
        logger.error("Failed to set MCTP link up.")
        return False

    if not ssh_util.run_command(ssh, "mctp addr", logger):
        logger.error("Failed to get MCTP address.")
        return False

    if not ssh_util.run_command(ssh, "mctp addr add 8 dev mctpi3c0", logger):
        logger.error("Failed to add MCTP address.")
        return False
    time.sleep(1)

    # Step 4: Learning MCTP endpoint
    logger.info("Learning MCTP endpoint...")
    learn_endpoint_command = "busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x1E"
    if not ssh_util.run_command(ssh, learn_endpoint_command, logger):
        logger.error(f"Failed to learn MCTP endpoint during cycle {cycle_num}.")
        return False

    # Step 5: Busctl tree and PLDM tool execution
    if not ssh_util.run_command(ssh, "busctl tree au.com.codeconstruct.MCTP1", logger):
        logger.error(f"Error detected in busctl during cycle {cycle_num}.")
        return False

    if not ssh_util.run_command(ssh, "pldmtool base GetTID -m 10", logger):
        logger.error(f"Failed to get TID during cycle {cycle_num}.")
        return False

    if not ssh_util.run_command(ssh, "pldmtool fw_update GetFwParams -m 10", logger):
        logger.error(f"Failed to get firmware parameters during cycle {cycle_num}.")
        return False

    # Step 6: Upload image file to BMC
    logger.info("Uploading image file to BMC...")
    img_path = "/home/billy/Desktop/meta/sitv3/sit/img/SB_SI_v31_0731_v2.pldm"  # Example path, update with your actual file
    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }
    if not ssh_util.push_file(target, img_path, remote_dir="/tmp/pldm_images"):
        logger.error(f"Failed to upload {img_path} to BMC.")
        return False

    time.sleep(5)

    # Step 7: Call busctl for PLDM
    if not ssh_util.run_command(ssh, "busctl tree xyz.openbmc_project.PLDM", logger):
        logger.error("Failed to call busctl for PLDM.")
        return False

    time.sleep(5)

    # Step 8: Set PLDM activation property
    logger.info("Activating PLDM...")
    activation_command = 'busctl set-property xyz.openbmc_project.PLDM /xyz/openbmc_project/software/142344108 xyz.openbmc_project.Software.Activation RequestedActivation s "xyz.openbmc_project.Software.Activation.RequestedActivations.Active"'
    if not ssh_util.run_command(ssh, activation_command, logger):
        logger.error(f"Failed to set PLDM activation during cycle {cycle_num}.")
        return False

    time.sleep(30)

    # Step 9: Final firmware parameter check
    if not ssh_util.run_command(ssh, "pldmtool fw_update GetFwParams -m 10", logger):
        logger.error(f"Failed to get firmware parameters during cycle {cycle_num} after activation.")
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

    # Run test cycles
    for cycle_num in range(1, total_cycles + 1):
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
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.15.221")
    args = parser.parse_args()
    main(args.ip)
