FROM debian:stable-slim

RUN apt update && apt install -y \
    qemu-system-misc \
    opensbi \
    u-boot-qemu \
    e2fsprogs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /riscv

#COPY image.qcow2 ./image.qcow2
COPY run_qemu.sh .

RUN chmod +x run_qemu.sh
