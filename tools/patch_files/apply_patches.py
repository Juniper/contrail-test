import ConfigParser
import platform
import subprocess
import shlex

def find_os():
    return platform.platform()

def find_sku():
    cmd = 'contrail-version|grep contrail-install | head -1 | awk \'{print $2}\''
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    try:
        stdout = stdout.split('~')
    except Exception as e:
        print 'Command returned None'
        return None
    return stdout[1].rstrip()

def ConfigSectionMap(Config , section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

def apply_patch(src,patch): 
    cmd = './tools/patch_files/patch_files.sh %s %s' % (str(src),str(patch),)
    args = shlex.split(cmd.encode('UTF-8'))
    print 'Attempting to patch file %s with patch file %s'%(str(src),str(patch))
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()
    try:
        print '%s'%str(stdout)
    except Exception as e:
        print 'Error in patching file %s'%str(src)    

def main():
    os = find_os()
    sku = find_sku()
    patch_file='tools/patch_files/patch_files.ini'
    Config = ConfigParser.ConfigParser()
    Config.read(patch_file)
    sections = Config.sections()
    for section in sections:
        ConfigSectionMap(Config,section)
        source = ConfigSectionMap(Config,section)['source']
        patchfile = ConfigSectionMap(Config,section)['patchfile']
        if 'os' in ConfigSectionMap(Config,section).keys():
            patch_os = ConfigSectionMap(Config,section)['os']
        else:
            patch_os = None
        if 'sku' in ConfigSectionMap(Config,section).keys():
            patch_sku = ConfigSectionMap(Config,section)['sku']
        else:
            patch_sku = None

        if patch_os and patch_sku:
            if (patch_os in os) and (patch_sku in sku):
                apply_patch(source,patchfile)
        elif patch_os and (not patch_sku):
            if (patch_os in os):
                apply_patch(source,patchfile)
        elif (not patch_os) and patch_sku:
            if (patch_sku in sku):
                apply_patch(source,patchfile)
        elif (not patch_os) and (not patch_sku):
                apply_patch(source,patchfile)

if __name__ == "__main__":
    main()
