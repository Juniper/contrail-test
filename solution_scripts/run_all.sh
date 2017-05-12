#!/bin/bash
while :
do
sh -x run_delete_all.sh
sh -x run_fat.sh
sh -x run_delete_all.sh
sh -x run_ipv4_v1_si.sh
sh -x run_delete_all.sh
sh -x run_ipv6_si.sh
sh -x run_delete_all.sh
sh -x run_mirror.sh
sh -x run_delete_all.sh
sh -x run_vn_flags.sh
sh -x run_delete_all.sh
sh -x run_create_global.sh
sh -x run_delete_all.sh
sh -x run_create_traffic_delete.sh
sh -x run_delete_all.sh
sh -x run_ipv4_v2_si.sh
sh -x run_delete_all.sh
done
