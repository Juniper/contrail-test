from fabric.operations import sudo,run,get,put,env

env.command_timeout = 60

def sudo_command(cmd):
    sudo(cmd)
def command(cmd):
    run(cmd)
def fput(src,dest):
    put(src,dest)


