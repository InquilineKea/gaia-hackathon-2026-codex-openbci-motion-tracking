set -eu
mount --make-rprivate /
mount -t tmpfs -o size=16m tmpfs /mnt
mkdir -p /mnt/job
mount --bind /tmp/collagen-parity /mnt/job
mount --bind /mnt/job/src /mnt/job/src
mount -o remount,bind,ro /mnt/job/src
mount --bind /mnt/job/runtime /mnt/job/runtime
mount -o remount,bind,ro /mnt/job/runtime
mount --bind /mnt/job/fixtures.json /mnt/job/fixtures.json
mount -o remount,bind,ro /mnt/job/fixtures.json
mount -t tmpfs -o size=16m tmpfs /home
mount -t tmpfs -o size=16m tmpfs /root
mount -t tmpfs -o size=16m tmpfs /run
mount -t tmpfs -o size=128m tmpfs /tmp
mount -t tmpfs -o size=64m tmpfs /dev/shm
exec setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs env -i PATH=/usr/bin:/bin HOME=/nonexistent OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0 LD_LIBRARY_PATH=/mnt/job/runtime/nvidia/cuda_nvrtc/lib OXT_SRC=/mnt/job/src OXT_OUT=/mnt/job/out OXT_CPU_LIBRARY=/mnt/job/out/liboxt_cpu.so OXT_FIXTURES=/mnt/job/fixtures.json OXT_NVRTC=/mnt/job/runtime/nvidia/cuda_nvrtc/lib/libnvrtc.so.12 sh /mnt/job/inside.sh
