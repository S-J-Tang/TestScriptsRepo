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

def push_file(self, target:dict, file_path:str):
    try:
        ip = target["ip"]
        file_name = file_path.split("/")[-1]
        t = paramiko.Transport((ip, 22))
        t.connect(username=target["username"], password=target["password"])
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.put(file_path, "/var/wcs/home/"+file_name)
        t.close()
        return True
    except Exception as e:
        self.logger.error(f"Fail to push {file_name} to {ip}, {e}")
        return False