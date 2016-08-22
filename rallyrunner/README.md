Rallyrunner
===========

Helper code to instal, configure and run openstack rally

# Custom scenarios
The purpose of this custom scenarios is to solve the complexity to add the scenarios especially if you want to add more
complex scenarios which would need somebody to play with jinja2 templates.

Rally scenario input contain at least three different stuffs -
1. scenario path, and its arguments
2. context configuration
3. runner configuration

This is trying reduce the complexity by dynamically generate rally input from the scenario arguments provided. It
populate runner and context configuration from the parameters provided which is easier than writing different
jinja2 templates. This custom scenario have below major files

1. scenario.yaml - This is the master jinja2 template which has macros to populate runner and context configuration
according to the parameters provided. It also add the scenario class path and arguments provided in scenarios directory.
In order to add new scenario, one have to create a new file which include a macro with the same name, which contain
scenario path and arguments. run_rally.py mentioned below use this template to dynamically generate rally inputs by
dynamically include those scenarios specific macros from scenarios directory with respect to the scenarios arguments
provided.
2. run_rally.py - this python script accept the rally task parameters as yaml input (as raw input or as an input file),
 and using scenario.yaml and scenario specific macros created under scenarios directory, it dynamically create rally
 task input and run rally. The random scenario class is added under rally/rally/plugins/openstack/complex/random_ops.py.
3. scenarios/random.yaml - This is a special scenario, which accept list of scenarios and run them in random manor, say
if there are scenarios scenario1, scenario2, scenario3 configured to run, in each iteration, the task will take one of
the scenarios in randomly and run it. In case of parallel task run, different threads would be running different
scenarios, which make it to load the system with near real scenarios.
Each scenario contain list of actions which is directly mapped to method names - so for a scenario, which have actions
"create network, create subnet, then boot a vm on that network", rally task will run them in the same order.

## Parameters accepted by run_rally.py

run_rally.py accept all parameters as a yaml input as either raw yaml input (task-args) or as yaml file (task-args-file)
It accepts global parameters which are used by scenario.yaml as well as individual scenario specific parameters which
are to be accepted and used by individual scenarios.

Example input file is as follows

```
{cxt_tenants: 1, cxt_users_per_tenant: 4, cxt_network: true, base_network_load_objects: 20, load_type: serial, times: 1,
scenario_args: { random: {image_id: 54e959d5-7632-4689-93d3-87c9eb5807a4, flavor_id: 1 }}}
```

scenario_args dictionary contain parameters for individual parameters, in the above example, the scenario "random" has
two parameters called image_id and flavor_id.

Please refer scenario.yaml for global arguments and individual scenario macros kept under scenarios directory for
scenario specific arguments.

## How to add new scenario
Just create one file under scenarios directory, which contain a jinja2 macro and would only setup scenario path as well
as scenario arguments. No need to setup context or runner, as it would be handled by scenario.yaml which can be
customized with the commandline arguments to run_rally.py.

In case scenario need to accept user inputs, make them as macro arguments and set them as scenario arguments in task
input, run_rally.py will pass those arguments to your scenario.

Below sample scenario macro accept two parameters - bar and baz (optional) and use them as scenario arguments.
```
{% macro foo(bar, baz=None) -%}
FooScenario.foo:
  -
  args:
    foo_arg: bar
    arg2: baz
```

## How to add new scenario in random_scenarios
You can add yet another item to random.yaml to add a new scenario with a list of actions. Actions are actually python
methods found under rally plugin code (rally/rally/plugins).

In case to add new actions, one have to add appropriate methods to rally plugin code.

It also accept two kind of parameters

1. user provided params as rally task input. E.g image id to boot node should be provided as task input
2. Instance variables created by the methods itself - say if a scenario have actions "create network, create subnet,
boot vm on the network which created right now". In order to make it worked, a method has been created named
 rs_create_network which create the network and save the network id as instance variable which can be used later within
 same scenario run. This variable can be accessed through __macro_<variable_name> called in the scenario args

```
 -
    - rs_create_network
    - _list_networks
    - _create_security_groups:
        params:
          num_security_groups: 1
    - _list_security_groups
    - _list_networks
    - _create_ports:
        params:
          network: __macro__rs_network
          security_groups: __macro__rs_security_group_ids
    - _list_networks
    - _list_ports

```

For example, in the above scenario, rs_create_network create the network and save a instance variable named rs_network,
and _create_security_groups create the security groups and save the ids in instance variable named rs_security_group_ids.
Later action __within the same scenario__ _create_ports use both the instance variables by setting up its params as
\__macro__<variable_name>.

## TODO
Need to convert inputs as json rather than yaml as yaml required indendation, it is easy to break the syntax.
