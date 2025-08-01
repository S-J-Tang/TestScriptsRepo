import paramiko
import requests
from requests import Request, Session
from requests_toolbelt import MultipartEncoder
import json
import urllib3
urllib3.disable_warnings()
from pprint import pprint
import time
import paramiko
import socket
import os
import logging
from datetime import date

def get_ssh_session(target:dict):
    connected = False
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(target["ip"], port=22, username=target["username"], password=target["password"])
        connected = True
    except paramiko.SSHException:
        pass
    except paramiko.ssh_exception.SSHException:
        pass
    except socket.timeout:
        pass
    except Exception:
        pass
    return connected, ssh

def push_file(target: dict, file_path: str, remote_dir: str = "/tmp/pldm_images", retries=3, delay=2):
    """
    Uploads a file to the specified remote directory on the target BMC.
    Ensures remote directory exists and retries on failure.
    """
    ip = target["ip"]
    file_name = os.path.basename(file_path)
    remote_path = f"{remote_dir}/{file_name}"

    for attempt in range(1, retries + 1):
        try:
            t = paramiko.Transport((ip, 22))
            t.connect(username=target["username"], password=target["password"])
            sftp = paramiko.SFTPClient.from_transport(t)

            # Ensure remote directory exists
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                sftp.mkdir(remote_dir)

            sftp.put(file_path, remote_path)
            sftp.close()
            t.close()

            logging.info(f"[Attempt {attempt}] Uploaded {file_path} to {remote_path}")
            return True

        except Exception as e:
            logging.warning(f"[Attempt {attempt}] Failed to upload: {e}")
            time.sleep(delay)

    logging.error(f"Upload failed after {retries} attempts: {file_path}")
    return False

def connect_bmc(ip, logger):
    """Connect to the BMC and return an SSH session."""
    target = {
        "ip": ip,
        "port": 22,
        "username": "root",
        "password": "0penBmc"
    }

    # Use the existing get_ssh_session function
    connected, ssh = get_ssh_session(target)
    if not connected:
        logger.error(f"Failed to connect to BMC at {ip}")
        sys.exit(1)

    logger.info(f"Connected to {ip}")
    return ssh

def run_command(ssh, command, logger):
    """Run a command on the BMC and handle output/error."""
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

def run_command_and_get_output(ssh, command, logger):
    """
    Run a command over SSH and return the output as a string.
    """
    try:
        logger.info(f"Running command: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        err_output = stderr.read().decode().strip()

        if err_output:
            logger.warning(f"Command stderr: {err_output}")
        logger.info(f"Command output: {output}")
        return output
    except Exception as e:
        logger.error(f"Exception while running command: {command}, error: {e}")
        return None
