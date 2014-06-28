import sys
import os
import select
import socket
import paramiko
import threading
import multiprocessing
import time
import commands
import subprocess


class SshConnect(threading.Thread):

    def __init__(self, remoteCmdExecuterObj):
        threading.Thread.__init__(self)

        self.remoteCmdExecuterObj = remoteCmdExecuterObj
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.load_host_keys(
            os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))

    def run(self):
        try:
            self.ssh.connect(self.remoteCmdExecuterObj.host,
                             username=self.remoteCmdExecuterObj.username,
                             password=self.remoteCmdExecuterObj.password)
        except:
            print("(pid %d) ssh to %s failed.." %
                  (os.getpid(), self.remoteCmdExecuterObj.host))
            return
        self.remoteCmdExecuterObj._ssh = self.ssh


class remoteCmdExecuter:

    def __init__(self):
        pass

    def execConnect(self, host, username, password):
        retry = 0
        self.host = host
        self.username = username
        self.password = password
        self._ssh = None
        return

        while self._ssh == None and retry < 100:
            retry += 1

            ''' This command hangs. Hence launch a thread in background and timeout '''
            t = SshConnect(self)
            t.start()
            t.join(10)

            if self._ssh != None:
                break

            time.sleep(5)
            if self._ssh == None and t.isAlive():
                print(
                    "************  %d. Kill frozen ssh connection to %s, retry" %
                    (retry, host))
                try:
                    t._Thread_stop()
                except:
                    print(
                        "%d. ssh to %s Thread could not be terminated!, ignore." %
                        (retry, host))

        if self._ssh == None:
            print("********* FATAL ********** SSH to %s failed!" % (host))

    def execCmd(self, cmd):
        ssh_conf_file_alternate = "-o UserKnownHostsFile=/dev/null -o strictHostKeyChecking=no"
        cmd = "sshpass -p %s ssh -q %s %s@%s '%s'" % (self.password,
                                                      ssh_conf_file_alternate, self.username, self.host, cmd)
        result = None
        try:
            result = subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError, e:
            pass
        return result

        stdin, stdout, stderr = self._ssh.exec_command(cmd)

        result = stdout.read()
        return result


def testRemoteCmdExecuter():
    aD = remoteCmdExecuter()
    aD.execConnect('10.84.7.250', 'root', 'Embe1mpls')
#   aD.execConnect( '10.84.7.42', 'root', 'c0ntrail123')

    #import pdb; pdb.set_trace ()
# print aD.execCmd ('ping 39.0.0.1 -I 10.84.7.42 -c 1 -W 1 | grep -i " 0%
# packet loss"')
    print aD.execCmd('cli show bgp summary | display xml')
#   print aD.execCmd ('ifsmon -Id | grep ROUTE')
#   print aD.execCmd ('cli -c "show bgp summary"')

if __name__ == "__main__":
    processList = []
    for i in range(1, 2):
        process = multiprocessing.Process(target=testRemoteCmdExecuter)
        process.start()
        processList.append(process)

    for process in processList:
        process.join()
