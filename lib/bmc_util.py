import lib.ssh_util as ssh_util
import time
from logging import Logger
from paramiko import SSHClient
import re

class SerialSSHClient:
    def __init__(self, ssh: SSHClient, port: str, logger: Logger, log_file= "default", rate = 57600):
        self.ssh = ssh
        self.port = "/dev/" + port
        self.log_file = "/tmp/" + port + ".log"
        if log_file != "default":
            self.log_file = "/tmp/" + log_file
        self.logger = logger
        self.pid = None
        self.rate = str(rate)
        self.setup_logging_process()

    def setup_logging_process(self):
        if self.pid:
            self.close()
        self.ssh.exec_command(f"stty -F {self.port} {self.rate} cs8 -cstopb -parenb -icanon -echo")
        self.ssh.exec_command(f"> {self.log_file}")
        stdin, stdout, stderr = self.ssh.exec_command(f"cat {self.port} >> {self.log_file} & echo $!")
        self.pid = stdout.readline()
        self.logger.info(f"Setup remote background process PID: {self.pid}")
        return 
    
    def send_command(self, command: str, clear_log_file= True, sleep= 0.1):
        if clear_log_file:
            self.ssh.exec_command(f"> {self.log_file}")
            time.sleep(sleep)
        self.ssh.exec_command(f'printf "{command}\\r" > "{self.port}"')
        time.sleep(sleep)
        stdin, stdout, stderr = self.ssh.exec_command(f"cat {self.log_file}")
        return self.__remove_ansi_escape(stdout.read().decode("utf-8", errors="ignore"))
    
    def log_inf(self):
        self.logger.info((self.return_log()))

    def return_log(self):
        stdin, stdout, stderr = self.ssh.exec_command(f"cat {self.log_file}")
        return self.__remove_ansi_escape(stdout.read().decode("utf-8", errors="ignore"))
    
    def clear_log(self):
        self.ssh.exec_command(f"> {self.log_file}")
        return
    
    def close(self):
        self.ssh.exec_command(f"rm {self.log_file}")
        command = f"""
        kill {self.pid};
        wait {self.pid} 2>/dev/null;
        """
        self.ssh.exec_command(command)
        self.logger.info(f"Remote background process PID closed")
        return
    
    def __remove_ansi_escape(self, text: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
