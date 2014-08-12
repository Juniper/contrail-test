from fabric.api import run
from fabric.context_managers import settings
import time


def restart_collector_to_listen_on_35999(self, collector_ip):
    try:
        with settings(host_string='%s@%s' % (self.inputs.username, collector_ip), password=self.inputs.password,
                      warn_only=True, abort_on_prompts=False):
            cmd = "grep 'syslog_port' /etc/contrail/collector.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + str(output) + "/c\  syslog_port=" + str(35999) \
                    + "' /etc/contrail/collector.conf"
                run('%s' % (cmd), pty=True)
                # Restart vizd if port no has been changed.
                cmd = "service contrail-collector restart"
                run('%s' % (cmd), pty=True)
                cmd = "service contrail-collector status | grep 'RUNNING' | wc -l"
                output = run('%s' % (cmd), pty=True)
                if int(output) == 0:
                    self.logger.error("contrail-collector service restart failure!!")
            else:
                cmd = "sed -i '/DEFAULT/ a \  syslog_port=" + \
                    str(35999) + "' /etc/contrail/collector.conf"
                run('%s' % (cmd), pty=True)
                # Restart vizd if port no has been changed.
                cmd = "service contrail-collector restart"
                run('%s' % (cmd), pty=True)
                cmd = "service contrail-collector status | grep 'RUNNING' | wc -l"
                output = run('%s' % (cmd), pty=True)
                if int(output) == 0:
                    self.logger.error("contrail-collector service restart failure!!")
    except Exception as e:
        self.logger.exception(
            "Got exception at restart_collector_to_listen_on_35999 as %s" %
            (e))
# end restart_collector_to_listen_on_35999


def update_rsyslog_client_connection_details(
        self,
        node_ip,
        server_ip='127.0.0.1',
        protocol='udp',
        port=35999,
        restart=False):
    try:
        with settings(host_string='%s@%s' % (self.inputs.username, node_ip), password=self.inputs.password,
                      warn_only=True, abort_on_prompts=False):

            if protocol == 'tcp':
                protocol = '@@'
            else:
                protocol = '@'
            connection_string = protocol + server_ip + ':' + str(port)

            cmd = "grep '@\{1,2\}[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + \
                    str(output) + "/c\*.* " + str(connection_string) + "' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '*.* " + connection_string + \
                    "' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            if restart is True:
                # restart rsyslog service
                cmd = "service rsyslog restart"
                run('%s' % (cmd), pty=True)
                cmd = "service rsyslog status | grep 'running' | wc -l"
                output = run('%s' % (cmd), pty=True)
                if int(output) == 0:
                    self.logger.error("rsyslog service restart failure!!")

    except Exception as e:
        self.logger.exception(
            "Got exception at update_rsyslog_client_connection_details as %s" %
            (e))

# end update_syslog_client_connection_details


def restart_rsyslog_client_to_send_on_35999(self, node_ip, server_ip):
    try:
        with settings(host_string='%s@%s' % (self.inputs.username, node_ip), password=self.inputs.password,
                      warn_only=True, abort_on_prompts=False):

            # update Working Directory in rsyslog.conf
            cmd = "grep 'WorkDirectory' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/$WorkDirectory/c\\\$WorkDirectory \/var\/tmp' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '$WorkDirectory /var/tmp' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            # update Queue file name in rsyslog.conf
            cmd = "grep 'ActionQueueFileName' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + \
                    str(output) + "/c\\\$ActionQueueFileName fwdRule1' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '$ActionQueueFileName fwdRule1' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            # update Max Disk Space for remote logging packets in
            # rsyslog.conf
            cmd = "grep 'ActionQueueMaxDiskSpace' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + \
                    str(output) + "/c\\\$ActionQueueMaxDiskSpace 1g' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '$ActionQueueMaxDiskSpace 1g' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            # update Queue save on shutdown
            cmd = "grep 'ActionQueueSaveOnShutdown' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + \
                    str(output) + "/c\\\$ActionQueueSaveOnShutdown on' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '$ActionQueueSaveOnShutdown on' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            # update Queue type
            cmd = "grep 'ActionQueueType' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + \
                    str(output) + "/c\\\$ActionQueueType LinkedList' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '$ActionQueueType LinkedList' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            # update Connection resume retry count
            cmd = "grep 'ActionResumeRetryCount' /etc/rsyslog.conf"
            output = run('%s' % (cmd), pty=True)
            if output:
                output = output.rstrip()
                cmd = "sed -i '/" + \
                    str(output) + "/c\\\$ActionResumeRetryCount -1' /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)
            else:
                cmd = "echo '$ActionResumeRetryCount -1' >> /etc/rsyslog.conf"
                run('%s' % (cmd), pty=True)

            # update rsyslog client-server connection details
            update_rsyslog_client_connection_details(self, node_ip, server_ip)

            # restart rsyslog service
            cmd = "service rsyslog restart"
            run('%s' % (cmd), pty=True)
            cmd = "service rsyslog status | grep 'running' | wc -l"
            output = run('%s' % (cmd), pty=True)
            if int(output) == 0:
                self.logger.error("rsyslog service restart failure!!")

    except Exception as e:
        self.logger.exception(
            "Got exception at restart_rsyslog_client_to_send_on_35999 as %s" %
            (e))

# end restart_rsyslog_client_to_send_on_35999
