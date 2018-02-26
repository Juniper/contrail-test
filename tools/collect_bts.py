import os
import re
import sys
import logging

from common.contrail_test_init import ContrailTestInit


logging.getLogger('paramiko.transport').setLevel(logging.WARN)

if __name__ == "__main__":
    init_obj = ContrailTestInit(sys.argv[1])
    init_obj.read_prov_file()
    ips = set(init_obj.cfgm_ips + init_obj.collector_ips)
    collected = {}
    for host_ip in ips:
        # copy the python script
        script_file = 'search-bt.py'
        ignore_tb_file = 'ignore_tracebacks.json'
        src_file = 'tools/%s' % (script_file)
        src_ignore_tb_file = 'tools/%s' % (ignore_tb_file)
        dest = '/tmp'

        containers = ['controller', 'analytics']

        for container in containers:
            if not init_obj.host_data[host_ip].get('containers', {}).get(container):
                container_str = ''
            else:
                container_str = container
            if collected.get('%s-%s' % (host_ip, container_str)):
                continue
            log_pattern = '%s/*%s*traceback*.log' % (dest, container_str)

            init_obj.copy_file_to_server(host_ip, src_file, dest, script_file,
                                         container=container, force=True)
            if os.path.exists(src_ignore_tb_file):
                init_obj.copy_file_to_server(host_ip,
                                             src_ignore_tb_file,
                                             dest,
                                             ignore_tb_file,
                                             container=container,
                                             force=True)
            init_obj.run_cmd_on_server(host_ip, 'rm -f %s' % (log_pattern))

            # Get the traceback files
            cmd = 'python %s/%s -p %s -i %s/%s' % (dest,
                                                   script_file,
                                                   dest,
                                                   dest,
                                                   ignore_tb_file
                                                   )
            if container_str:
                cmd = cmd + ' -l %s' % (container_str)
            output = init_obj.run_cmd_on_server(host_ip, cmd)
            print output

            # Copy the resulting log files
            if 'Done looking for' in output:
                dest_folder = 'logs'
                result_files = re.findall(r'will be in (.*)\n', output)
                for f in result_files:
                    init_obj.copy_file_from_server(host_ip, f.strip(),
                                                   dest_folder, container=container)
                collected['%s-%s' % (host_ip, container_str)] = True
        # end for container
    # end for host_ip
