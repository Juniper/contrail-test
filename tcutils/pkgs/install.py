"""Module to build and install specific package in a specific host."""

import os
import importlib
import logging as LOG
from time import sleep

from fabric.api import run
from fabric.operations import put
from fabric.context_managers import settings, hide
from tcutils.util import run_fab_cmd_on_node, fab_put_file_to_vm

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)

SETUP_SCRIPT = 'setup.py'


class SSHError(Exception):
    pass


def build_pkg(pkgdir, pkgsrc, log=LOG):
    """Builds the specific package.

    Requires setup.py to be present in the "pkgdir"
    """
    builder = Builder(pkgdir, pkgsrc, log)
    return builder.build()


def install_pkg(pkgdir, pkgdst, log=LOG):
    """Copies the package to the specific host
    and installs it in the site-packages.

    Requires setup.py to be present in the "pkgdir"
    """
    installer = Installer(pkgdir, pkgdst, log)
    return installer.install()


def build_and_install(pkgdir, pkgsrc, pkgdst, log=LOG):
    """Builds the specific package, copies it to the specific host
    and installs it in the site-packages.

    Requires setup.py to be present in the "pkgdir"
    """
    pass
    builder = Builder(pkgdir, pkgsrc, log)
    if not builder.build():
        return False

    installer = Installer(pkgdir, pkgsrc, pkgdst, log)
    return installer.install()


class PkgHost(object):

    def __init__(self, host, vm_node_ip=None, user="root", password="C0ntrail123", key=None):
        self.host = host
        # if None vm_node_ip is same as the host.
        if not vm_node_ip:
            self.vm_node_ip = host
        else:
            self.vm_node_ip = vm_node_ip
        self.user = user
        self.password = password
        self.key = key


class BuildInstallBase(object):

    def __init__(self, pkgdir, pkgsrc, log):
        self.pkgsrc = pkgsrc
        self.log = log
        pkg = importlib.import_module('tcutils.pkgs.%s' % pkgdir)
        pkg = os.path.abspath(pkg.__file__)
        self.log.debug("pkg path: %s", pkg)
        # If already complied.
        self.pkg_path = pkg.replace("__init__.pyc", "")
        self.pkg_path = self.pkg_path.replace("__init__.py", "")
        self.dist_path = os.path.join(self.pkg_path, "dist")

    def build(self):
        pass

    def install(self):
        pass


class Builder(BuildInstallBase):

    def __init__(self, pkgdir, pkgsrc, log):
        super(Builder, self).__init__(pkgdir, pkgsrc, log)

    def build(self):
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.pkgsrc.user,
                                                 self.pkgsrc.host),
                          password=self.pkgsrc.password, warn_only=True,
                          abort_on_prompts=False):
                if os.path.isfile(os.path.join(self.pkg_path, SETUP_SCRIPT)):
                    run("cd %s; python %s sdist" %
                        (self.pkg_path, SETUP_SCRIPT))
                else:
                    self.log.error("No setup script found at: %s" %
                                   self.pkg_path)
                    return False

        return True


class Installer(BuildInstallBase):

    def __init__(self, pkgdir, pkgsrc, pkgdst, log):
        super(Installer, self).__init__(pkgdir, pkgsrc, log)
        self.pkgdst = pkgdst

    def copy_to_vm(self, pkg, host):
        output = None
        self.log.debug("Copying Package %s to VM" % (str(pkg)))
        try:
            with hide('everything'):
                with settings(host_string='%s@%s' % (self.pkgsrc.user, host),
                              password=self.pkgsrc.password, warn_only=True,
                              abort_on_prompts=False):
                    output = fab_put_file_to_vm(host_string='%s@%s' % (
                        self.pkgdst.user, self.pkgdst.host),
                        password=self.pkgdst.password, src=pkg,
                        dest='~/',
                        logger=self.log)
                    self.log.debug(str(output))
                    self.log.debug(
                        "Copied the distro from compute '%s' to VM '%s'", host, self.pkgdst.host)
        except Exception, errmsg:
            self.logger.exception(
                "Exception: %s occured when copying %s" % (errmsg, pkg))
        finally:
            return

    def execute_in_vm(self, cmd, host):
        output = None
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.pkgsrc.user, host),
                          password=self.pkgsrc.password, warn_only=True,
                          abort_on_prompts=False):
                retry = 6
                while True:
                    output = ''
                    output = run_fab_cmd_on_node(
                        host_string='%s@%s' % (
                            self.pkgdst.user, self.pkgdst.host),
                        password=self.pkgdst.password, cmd=cmd,
                        as_sudo=True,
                        logger=self.log)
                    if ("Connection timed out" in output or
                            "Connection refused" in output) and retry:
                        self.log.debug(
                            "SSH timeout, sshd might not be up yet. will retry after 5 secs.")
                        sleep(5)
                        retry -= 1
                        continue
                    elif "Connection timed out" in output:
                        raise SSHError(output)
                    else:
                        break
        self.log.debug(output)
        return output

    def install(self):
        # Look for the pkg  distro.
        with hide('everything'):
            with settings(host_string='%s@%s' % (self.pkgsrc.user,
                                                 self.pkgsrc.host), password=self.pkgsrc.password,
                          warn_only=True, abort_on_prompts=False):
                distro = run("cd %s; ls" % self.dist_path)
                if (distro == '' or "No such file or directory" in distro):
                    self.log.error(
                        "No distribution package found at: %s, Build one." %
                        self.dist_path)
                    return False

        # copy distro to the compute node/node in which the vm is present.
        pkgsrc_host = self.pkgsrc.host
        dist_path = self.dist_path
        if self.pkgsrc.host != self.pkgsrc.vm_node_ip:
            self.log.debug("Cfgm and compute are different; copy the distro from  cfgm '%s'"
                           " to compute '%s'", self.pkgsrc.host, self.pkgsrc.vm_node_ip)
            pkgsrc_host = self.pkgsrc.vm_node_ip
            dist_path = "/tmp/"
            with hide('everything'):
                with settings(host_string='%s@%s' % (self.pkgsrc.user,
                                                     pkgsrc_host),
                              password=self.pkgsrc.password, warn_only=True,
                              abort_on_prompts=False):
                    put(os.path.join(self.dist_path, distro), dist_path)
                    self.log.debug(
                        "Copied the distro to compute '%s'", pkgsrc_host)

        # Copy the pkg to VM and install in it.
        distro_dir = distro.replace(".tar.gz", "")
        scpout = self.copy_to_vm(os.path.join(dist_path, distro), pkgsrc_host)
        self.log.debug(scpout)
        # Remove the distro dir if present
        out = self.execute_in_vm("rm -rf %s" % distro_dir, pkgsrc_host)
        out = self.execute_in_vm("tar -xvzf %s" % distro, pkgsrc_host)
        self.log.debug(out)
        out = self.execute_in_vm("cd %s; python %s install" % (distro_dir,
                                 SETUP_SCRIPT), pkgsrc_host)
        self.log.debug(out)

        return True
