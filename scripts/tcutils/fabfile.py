from fabric.operations import sudo,run,get,put
def sudo_command(cmd):
    sudo(cmd)
def command(cmd):
    run(cmd)
def fput(src,dest):
    put(src,dest)


