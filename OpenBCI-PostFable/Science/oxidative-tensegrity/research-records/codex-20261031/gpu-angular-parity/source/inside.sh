set -eu
[ "$(id -u)" = 65534 ]
[ ! -e /home/ubuntu ]
[ ! -e /root/.ssh ]
g++ -std=c++17 -O2 -ffp-contract=off -fPIC -shared /mnt/job/src/cpu.cpp -o /mnt/job/out/liboxt_cpu.so
exec sh /mnt/job/src/nebius_parity.sh
