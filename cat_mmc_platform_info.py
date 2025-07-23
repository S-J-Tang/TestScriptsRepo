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

def run_test_cycle(ip, cycle_num, logger):
    logger.info(f"Running test cycle {cycle_num}...")

    # Connect to BMC
    ssh = connect_bmc(ip, logger)

    # Display usb port
    logger.info("Reading /etc/os-release...")
    stdin, stdout, stderr = ssh.exec_command("lsusb -vt")
    logger.info(stdout.read().decode())

    """
    if you want to write ten times per lopp as below command:

    LOG=/tmp/uart.log; PORT=/dev/ttyUSB1;
    stty -F "$PORT" 57600 cs8 -cstopb -parenb -icanon -echo;
    > "$LOG";
    cat "$PORT" >> "$LOG" & CATPID=$!;
    sleep 2;
    for i in {0..10};
    do printf "platform info\r" > "$PORT"; sleep 0.1; done; sleep 2;
    kill "$CATPID";
    wait "$CATPID" 2>/dev/null;
    cat "$LOG"

    """
    # Display mmc platform info
    logger.info("Reading mmc platform info...")
    command = '''
    LOG=/tmp/uart.log; PORT=/dev/ttyUSB5; 
    stty -F "$PORT" 57600 cs8 -cstopb -parenb -icanon -echo; 
    > "$LOG"; 
    cat "$PORT" >> "$LOG" & CATPID=$!; 
    sleep 2; 
    printf "platform info\r" > "$PORT"; 
    sleep 2; 
    kill "$CATPID"; 
    wait "$CATPID" 2>/dev/null; 
    cat "$LOG"
    '''
    stdin, stdout, stderr = ssh.exec_command(command)
    logger.info(stdout.read().decode())

    ssh.close()
    return True  # Cycle passed

def main(ip):
    # Initialize logger
    logger = init_logger("bmc_reboot.log", verbose=True)

    # Run 1 test cycles
    for cycle_num in range(1, 2):
        success = run_test_cycle(ip, cycle_num, logger)
        if not success:
            logger.error(f"Test cycle {cycle_num} failed. Stopping further tests.")
            break
        time.sleep(2)  # Delay between cycles to avoid continuous strain

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", help="Target BMC IP address", default="10.10.14.229")  # Default IP set here
    args = parser.parse_args()
    main(args.ip)
