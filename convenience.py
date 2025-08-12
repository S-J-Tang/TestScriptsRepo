import paramiko
import argparse
import sys
import time
import lib.ssh_util as ssh_util
import lib.bmc_boot_utils as bbu
from lib.init_logger import init_logger
import lib.bmc_util as bu
import random
import shutil

fw_map = {
    "pcie": "/home/adam/meta/OpenBIC_project/meta_OpenBIC/pldm_fw_creator/new.pldm",
    "bic": "/home/adam/meta/OpenBIC_project/meta_OpenBIC/build/zephyr/SB_SI.pldm"
}

logger = init_logger("bmc_reboot.log", verbose=True)

def ac(ssh):
    ssh_util.run_command(ssh, "mfg-tool power-control -p 0 -s standby -a cycle", logger)

def dc_power_on(ssh):
    ssh.exec_command("i2cset -f -y 21 0x33 0x38 0x01")
    time.sleep(5)

def fw_update(ssh, ip, component="bic"):
    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }

    if not ssh_util.push_file(target, fw_map[component]):
        print("push file: Fail")
        return False
    ssh.exec_command("echo 1 > /sys/bus/i3c/devices/i3c-0/hotjoin")
    time.sleep(5)
    if not ssh_util.run_command(ssh, "busctl set-property xyz.openbmc_project.PLDM /xyz/openbmc_project/software/142344108 \
                         xyz.openbmc_project.Software.Activation RequestedActivation s \
                            \"xyz.openbmc_project.Software.Activation.RequestedActivations.Active\"", logger): 
        print("fw update fail")
    
def mctp_link(ssh, *args):
    command = f"""
    mctp link;
    mctp link set mctpi3c0 up;
    mctp addr;
    mctp addr add 8 dev mctpi3c0;
    """
    ssh.exec_command(command)
    time.sleep(0.1)
    for i, arg in enumerate(args):
        command = f"""
        busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpi3c0 au.com.codeconstruct.MCTP.BusOwner1 \
            LearnEndpoint ay 6 0x06 0x32 0x12 0x34 0x55 0x{arg};
        """
        ssh_util.run_command(ssh, command, logger)
    ssh_util.run_command(ssh, "busctl tree au.com.codeconstruct.MCTP1", logger)

def mmc_log_record(ssh):
    mmcs = ["tty_SITV_0", "tty_SITV_1", "tty_SITV_2", "tty_SITV_3"]
    for i in range(len(mmcs)):
        mmcs[i] = bu.SerialSSHClient(ssh, mmcs[i], logger)
    while (input("enter 0 to exit : ") != "0"):
        for mmc in mmcs:
            logger.info(f"-------sitv {mmc.port[-1]}--------")
            # mmc.send_command("platform info")
            mmc.log_inf()
            mmc.clear_log()
    for mmc in mmcs:
        mmc.close()

            
def main(ip):
    ssh = ssh_util.connect_bmc(ip, logger)
    # mmc_log_record(ssh)
    mctp_link(ssh, 40)
    fw_update(ssh, ip, "pcie")




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.14.94")  # Default IP set here
    args = parser.parse_args()
    main(args.ip)