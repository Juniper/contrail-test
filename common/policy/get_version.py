import re


def get_OsVersion(self):
    OSVersion = self.inputs.os_type[self.inputs.compute_ips[0]]
    OSVersion = OSVersion.capitalize()
    return OSVersion
# end get_OsVersion


def get_VrouterReleaseVersion(self):
    buildlist = []
    myBuild = self.inputs.run_cmd_on_server(
        self.inputs.compute_ips[0], 'contrail-version | grep contrail-vrouter-agent | awk \'{print $2}\'',
        container='agent')
    myRel = myBuild.split("-", 1)
    return myRel[0]
# end get_VrouterReleaseVersion


def get_VrouterBuildVersion(self):
    buildlist = []
    myBuild = self.inputs.run_cmd_on_server(
        self.inputs.compute_ips[0], 'contrail-version | grep contrail-vrouter-agent | awk \'{print $3}\'',
        container='agent')
    return myBuild
# end get_VrouterBuildVersion


def get_OS_Release_BuildVersion(self):
    BuildTag = str(get_OsVersion(self)) + '-' + str(get_VrouterReleaseVersion(self)) + \
        '-' + str(get_VrouterBuildVersion(self))
    return BuildTag
# end get_OS_Release_BuildVersion
