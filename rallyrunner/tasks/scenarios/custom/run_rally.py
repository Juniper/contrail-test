import jinja2
import argparse
import tempfile
import os
import fnmatch
import subprocess
import sys
import yaml

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class RallyRunner():
    def __init__(self, rally_task_args=None,
                 template_file='scenario.yaml',
                 scenario_directory='scenarios'):
        self.template_file = template_file
        self.scenario_directory = scenario_directory
        self.rally_task_args = rally_task_args
        self.rally_scenarios = self.rally_task_args.get('scenarios', [])
        self.template = None

    @jinja2.contextfunction
    def get_context(self, c):
        return c

    def get_scenario_args(self, scenario):
        """ Return scenario arguments in the format "param1=value1, param2=value2"
        :param scenario: scenario name
        :return: scenario arguments, None if no scenario arguments
        """
        args = ','.join(["{}='{}'".format(k,v) for k,v in self.rally_task_args.get('scenario_args', {}).get(scenario, {}).iteritems()])
        return args

    def create_rally_input(self, fp):

        jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(THIS_DIR),
                                  trim_blocks=True)
        if self.rally_scenarios:
            scenario_details = {
                self.scenario_directory + '/' + x: ({ os.path.splitext(x)[0]: self.get_scenario_args(os.path.splitext(x)[0])} if self.get_scenario_args(os.path.splitext(x)[0])
                else os.path.splitext(x)[0])
                for x in os.listdir(self.scenario_directory)
                if os.path.isfile(self.scenario_directory + os.sep + x) and fnmatch.fnmatch(
                self.scenario_directory + os.sep + x, '*.yaml') and os.path.splitext(x)[0] in self.rally_scenarios
                }
        else:
            scenario_details = {
                self.scenario_directory + '/' + x: ({ os.path.splitext(x)[0]: self.get_scenario_args(os.path.splitext(x)[0])} if self.get_scenario_args(os.path.splitext(x)[0])
                else os.path.splitext(x)[0])
                for x in os.listdir(self.scenario_directory)
                if os.path.isfile(self.scenario_directory + os.sep + x) and fnmatch.fnmatch(
                self.scenario_directory + os.sep + x, '*.yaml')
                }

        scenarios = {
            i: (''.join(j.keys()) if isinstance(j, dict) else j)
            for i, j in scenario_details.iteritems()
        }

        template = jenv.get_template(self.template_file)
        template.globals['context'] = self.get_context
        template.globals['callable'] = callable
        context = {'scenario_details': scenario_details, 'scenarios': scenarios}
        footer = (template.render(**context))
        if fp:
            os.write(fp, footer)
        os.close(fp)

    # rally task start scenario.yaml --task-args "{cxt_tenants: 1, cxt_users_per_tenant: 4, cxt_network: true, base_network_load_objects: 30, load_type: serial, times: 1, scenarios: [create_and_list_networks, random]}"
    @staticmethod
    def run_rally(template_file, task_args=None, task_args_file=None):
        cmd = ['rally', 'task', 'start', template_file]
        if task_args:
            cmd.extend(['--task-args', task_args])
        elif task_args_file:
            cmd.extend(['--task-args-file', task_args_file])

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        while True:
            next_out = p.stdout.readline()
            yield (next_out)
            if next_out == '' and p.poll() != None:
                break


def main(argv=sys.argv):
    scenarios = []
    ap = argparse.ArgumentParser(
        description="Run rally tasks")
    ap.add_argument("--task-args", type=str,
                    help="""Rally task parameters - a yaml dictionary
                    with the parameters""")
    ap.add_argument("--task-args-file", type=str,
                    help="""It should be either a yaml file which contains
                     all arguments""")
    args = ap.parse_args()
    if args.task_args and args.task_args_file:
        raise argparse.ArgumentError('Either one of task-args or task-args-file to be provided')

    if not args.task_args and not args.task_args_file:
        raise argparse.ArgumentError('Either one of task-args or task-args-file to be provided')

    if args.task_args_file:
        with open(args.task_args_file, 'r') as stream:
            rally_task_args = yaml.load(stream)

    if args.task_args:
        rally_task_args = yaml.load(args.task_args)

    rr = RallyRunner(rally_task_args=rally_task_args)

    (fp, file) = tempfile.mkstemp(dir=THIS_DIR)
    try:
        rr.create_rally_input(fp)
        for out in rr.run_rally(file, task_args=args.task_args, task_args_file=args.task_args_file):
            sys.stdout.write(out)
            sys.stdout.flush()
    finally:
        os.remove(file)

    return True


if __name__ == "__main__":
    sys.exit(not main(sys.argv))
