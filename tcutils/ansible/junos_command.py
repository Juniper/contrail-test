---
- name: Get device information
  hosts: localhost
  roles:
    - Juniper.junos
  connection: local
  gather_facts: no

  tasks:
    - name: Get "{{ command }}" output
      juniper_junos_command:
        commands:
          - "{{ command }}"
        port: 22
        host: "{{ host }}"
        dest: "{{ json }}"
        formats: json
        return_output: false
