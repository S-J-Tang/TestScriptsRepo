import argparse
import sys
import time
import re
import lib.ssh_util as ssh_util
import lib.bmc_boot_utils as bbu
from lib.init_logger import init_logger
import os

def run_test_cycle(ip, cycle_num, logger):
    logger.info(f"Running test cycle {cycle_num}...")

    # Connect to BMC
    ssh = ssh_util.connect_bmc(ip, logger)

    # Run Setup Steps only for the first cycle
    if cycle_num == 1:

        # AC BMC
        ssh.exec_command("mfg-tool power-control -p 0 -s standby -a cycle")
        logger.info("AC command sent. BMC is restarting...")

        # Wait for BMC to reboot and reconnect
        time.sleep(10)
        if not bbu.wait_bmc_reboot_connection({"ip": ip, "port": 22, "username": "root", "password": "0penBmc"}, timeout=600):
            logger.error(f"BMC reboot check failed in cycle {cycle_num}.")
            return False  # Cycle failed
        time.sleep(1)
        
        # Connect to BMC
        ssh = ssh_util.connect_bmc(ip, logger)
        
        # Step 1: Hotjoin command for I3C bus
        logger.info("Hotjoining I3C bus...")
        if not ssh_util.run_command(ssh, "echo 1 > /sys/bus/i3c/devices/i3c-0/hotjoin", logger):
            logger.error("Failed to hotjoin I3C bus.")
            return False

        # Step 2.1: I2C set command
        logger.info("Setting I2C device...")
        if not ssh_util.run_command(ssh, "i2cset -y 10 0x21 0x40", logger):
            logger.error("Failed to set I2C device.")
            return False
        time.sleep(1)

        # Step 2.2: I2C set command
        logger.info("Setting I2C device...")
        if not ssh_util.run_command(ssh, "i2cset -y 13 0x21 0x41", logger):
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

        # Step 4.1: Learning MCTP endpoint
        logger.info("Learning MCTP endpoint...")
        learn_endpoint_command = "busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x10"
        if not ssh_util.run_command(ssh, learn_endpoint_command, logger):
            logger.error(f"Failed to learn MCTP endpoint during cycle {cycle_num}.")
            return False

        time.sleep(5)

        # Step 4.2: Learning MCTP endpoint (again)
        logger.info("Learning MCTP endpoint...")
        learn_endpoint_command = "busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x20"
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

        time.sleep(1)

        if not ssh_util.run_command(ssh, "pldmtool fw_update GetFwParams -m 10", logger):
            logger.error(f"Failed to get firmware parameters during cycle {cycle_num}.")
            return False

        time.sleep(2)

        if not ssh_util.run_command(ssh, "pldmtool base GetTID -m 20", logger):
            logger.error(f"Failed to get TID during cycle {cycle_num}.")
            return False

        time.sleep(1)

        if not ssh_util.run_command(ssh, "pldmtool fw_update GetFwParams -m 20", logger):
            logger.error(f"Failed to get firmware parameters during cycle {cycle_num}.")
            return False

    # Step 6: Loop through images and upload each image with dynamic name
    image_files = ["SB_SI_v29_0731_v2.pldm", "SB_SI_v31_0731_v2.pldm"]  # List of images to upload

    # Determine which image to upload based on the cycle number
    # Alternate between v29 and v31 for even and odd cycles
    if cycle_num % 3 == 0:
        image_to_upload = "SB_SI_v29_0731_v2.pldm"  # For every 3rd cycle, always upload v29
    else:
        image_to_upload = image_files[cycle_num % 2]  # Alternate images for other cycles

    logger.info(f"Uploading image: {image_to_upload} to BMC...")

    # Get the current working directory and build the relative path to the image file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(script_dir, "img", image_to_upload)

    if not os.path.isfile(img_path):
        logger.error(f"Image file not found: {img_path}")
        return False

    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }

    time.sleep(10)

    remote_img_path = f"/tmp/pldm_images/{cycle_num}.pldm"  # Renaming the image as {cycle_num}.pldm

    # Upload the image to the BMC
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
    logger.info(f"Activating PLDM for image {cycle_num}...")
    activation_command = 'busctl set-property xyz.openbmc_project.PLDM /xyz/openbmc_project/software/142344108 xyz.openbmc_project.Software.Activation RequestedActivation s "xyz.openbmc_project.Software.Activation.RequestedActivations.Active"'
    if not ssh_util.run_command(ssh, activation_command, logger):
        logger.error(f"Failed to set PLDM activation during cycle {cycle_num}.")
        return False

    time.sleep(120)

    # Step 9: Final firmware parameter check
        # Step 9: Final firmware parameter check for EID 10 and EID 20
    logger.info("Verifying firmware version after activation...")

    # Set expected version based on the image being used
    expected_version = None
    if "v29" in image_to_upload:
        expected_version = "2025.29.01"
    elif "v31" in image_to_upload:
        expected_version = "2025.31.01"

    # Verify EID 10
    output1 = ssh_util.run_command_and_get_output(ssh, "pldmtool fw_update GetFwParams -m 10", logger)
    if output1 is None:
        logger.error("No output from GetFwParams -m 10")
        return False

    match1 = re.search(r'"ActiveComponentImageSetVersionString":\s*"(\d{4}\.\d{2}\.\d{2})"', output1)
    actual_version_10 = match1.group(1) if match1 else None

    if actual_version_10 != expected_version:
        logger.error(f"EID 10 version mismatch. Expected: {expected_version}, Got: {actual_version_10}")
        return False
    else:
        logger.info(f"EID 10 firmware version verified: {actual_version_10}")

    time.sleep(10)

    # Verify EID 20
    output2 = ssh_util.run_command_and_get_output(ssh, "pldmtool fw_update GetFwParams -m 20", logger)
    if output2 is None:
        logger.error("No output from GetFwParams -m 20")
        return False

    match2 = re.search(r'"ActiveComponentImageSetVersionString":\s*"(\d{4}\.\d{2}\.\d{2})"', output2)
    actual_version_20 = match2.group(1) if match2 else None

    if actual_version_20 != expected_version:
        logger.error(f"EID 20 version mismatch. Expected: {expected_version}, Got: {actual_version_20}")
        return False
    else:
        logger.info(f"EID 20 firmware version verified: {actual_version_20}")

    # Close the SSH session
    ssh.close()
    return True  # Cycle passed

def main(ip):
    # Initialize logger
    logger = init_logger("MMC_FW_update_stress.log", verbose=True)

    # Track the number of failed cycles
    failure_count = 0
    total_cycles = 10  # Total number of test cycles

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
