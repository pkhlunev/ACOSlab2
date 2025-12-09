#!/bin/bash

echo "[+] Starting QEMU RISC-V VM..."

exec qemu-system-riscv64 -machine 'virt' -cpu 'rv64' -m 1G \
	-device virtio-blk-device,drive=hd \
	-drive file=image.qcow2,if=none,id=hd \
	\
	-fsdev local,id=fs1,path=/mnt/shared,security_model=none \
	-device virtio-9p-device,fsdev=fs1,mount_tag=hostshare \
	\
	-device virtio-net-device,netdev=net \
	-netdev user,id=net,hostfwd=tcp:127.0.0.1:2222-:22 \
	-kernel /usr/lib/u-boot/qemu-riscv64_smode/uboot.elf \
	\
	-object rng-random,filename=/dev/urandom,id=rng \
	-device virtio-rng-device,rng=rng \
	\
	-nographic \
	-append 'root=LABEL=rootfs console=ttyS0'
