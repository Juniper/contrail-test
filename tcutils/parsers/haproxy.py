import re
from fabric.api import run
from fabric.context_managers import settings, hide
from fabric.contrib.files import exists
from collections import defaultdict

'''
   Parses haproxy conf file and produces a dict output of the same
   Inputs:
      filename: Absolute path of the haproxy.conf file
   Output:
      dict of the below format (comparable to lbaasv2 object model)
      {'frontends': [{'uuid': <listener_uuid>,
                      'address': <vip_ip>,
                      'port': <vip_protocol_port>,
                      'protocol': <tcp/http/https>,
                      'backend': <pool_uuid>,
                     },
                    ],
       'backends': [{'uuid': <pool_uuid>,
                     'protocol': <tcp/http/https>,
                     'lb_method': <roundrobin,source,leastconn>,
                     'members': [{'uuid': <member_id>,
                                  'port': <protocol_port>,
                                  'address': <member_ip>,
                                 },
                                ],
                     'healthmonitor': {'timeout': <timeout>,
                                       'retries': <retries>,
                                       'delay': <interval>,
                                       'method': <ping/tcp/http/https>,
                                      },
                     },
                    ],
      }
'''

def parse_haproxy(filename, host, username, password):
    haproxy_dict = defaultdict(list)
    with settings(hide('everything'), host_string='%s@%s' %(username, host),
                  password=password, warn_only=True, abort_on_prompts=False):
        if not exists(filename):
            return None
        output = run('cat %s'%filename)
    keywords = ['frontend', 'backend', 'global', 'defaults']
    pattern = '(?:^|\n)\s*(?:{})'.format('|'.join(map(re.escape, keywords)))
    iters = re.finditer(pattern, output)
    indices = [match.start() for match in iters]
    matches = map(output.__getslice__, indices, indices[1:] + [len(output)])

    for match in matches:
        match = match.strip()
        if match.startswith('frontend'):
            haproxy_dict['frontends'].append(get_vip_dict(match))
        elif match.startswith('backend'):
            haproxy_dict['backends'].append(get_pool_dict(match))
    return haproxy_dict

def get_vip_dict(lines):
    vip_dict = dict()
    for line in lines.split('\n'):
        line = line.strip()
        if 'frontend' in line:
            vip_dict['uuid'] = re.match('frontend\s+(.*)', line).group(1)
        elif 'bind' in line:
            m = re.match('bind\s+(.*):([0-9]+)', line)
            vip_dict['address'] = m.group(1)
            vip_dict['port'] = int(m.group(2))
        elif 'mode' in line:
            vip_dict['protocol'] = re.match('mode\s+(\w+)', line).group(1)
        elif 'backend' in line:
            vip_dict['backend'] = re.match('default_backend\s+(.*)', line).group(1)
    return vip_dict

def get_pool_dict(lines):
    pool_dict = defaultdict(list)
    for line in lines.split('\n'):
        line = line.strip()
        if 'backend' in line:
            pool_dict['uuid'] = re.match('backend\s+(.*)', line).group(1)
        elif 'mode' in line:
            pool_dict['protocol'] = re.match('mode\s+(\w+)', line).group(1)
        elif 'balance' in line:
            pool_dict['lb_method'] = re.match('balance\s+(\w+)', line).group(1)
        elif 'timeout' in line:
            pool_dict['timeout'] = re.match('timeout\s+check\s+([0-9]+)s', line).group(1)
        elif 'server' in line:
            if 'timeout' in pool_dict:
                m = re.match('server\s+(.*)\s+(.*):([0-9]+)\sweight\s([0-9]+)\scheck\sinter\s([0-9]+)s\sfall\s([0-9]+)', line)
                pool_dict['members'].append({'uuid': m.group(1),
                                         'address': m.group(2),
                                         'port': m.group(3),
                                         'weight': int(m.group(4)),
                                         'delay': int(m.group(5)),
                                         'retries': int(m.group(6))})
            else:
                m = re.match('server\s+(.*)\s+(.*):([0-9]+) weight ([0-9]+)', line)
                pool_dict['members'].append({'uuid': m.group(1),
                                         'address': m.group(2),
                                         'port': m.group(3),
                                         'weight': m.group(4)})
    return pool_dict

if __name__ == '__main__':
    print parse_haproxy('/root/haproxy.cfg', '127.0.0.1', 'root', 'c0ntrail123')
