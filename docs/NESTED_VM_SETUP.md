# NEXUS Nested VM Setup (Triple-Nested Virtualization)

## Overview

This guide explains the triple-nested virtualization architecture available in NEXUS:

```
Host OS (Mac/Windows/Linux)
  └─ QEMU Hypervisor
      └─ Ubuntu Linux VM (with Docker + KVM)
          └─ Docker Container (nexus-playground)
              └─ Optional: Inner KVM VMs
```

## Auto-Installation

The `init-qemu-nested-vm.sh` script handles everything automatically:

```bash
./scripts/init-qemu-nested-vm.sh
```

This will:
1. Detect your OS (Mac/Linux/Windows)
2. Install QEMU if not present (Homebrew on Mac, apt on Linux)
3. Download Ubuntu 24.04 LTS (ARM64)
4. Create QCOW2 disk (20GB)
5. Generate cloud-init configuration with Docker + KVM pre-installed
6. Create startup scripts

## Quick Start

```bash
# Auto-install and scaffold (one-time, ~10 min)
./scripts/init-qemu-nested-vm.sh

# Start the nested VM
~/.nexus-nested-vm/start-nested-vm.sh

# Connect via SSH
~/.nexus-nested-vm/connect-ssh.sh
# Or: ssh -p 2222 ubuntu@localhost
```

## Architecture Layers

| Layer | Technology | Security | Performance |
|-------|-----------|----------|-------------|
| 1. Host | Mac/Windows/Linux | Host OS security | Native |
| 2. Hypervisor | QEMU | Hardware isolation | ~85-90% |
| 3. VM | Ubuntu + Docker | Namespace isolation | ~70-80% |
| 4. Container | Docker | cgroup/namespace | ~60-70% |
| 5. Inner VM | KVM (optional) | Hardware VM | ~40-50% |

## Use Cases

### Standard Setup (Layers 1-4)
```
Host → QEMU → VM with Docker → Docker Container (nexus-playground)
Performance: Good | Security: Strong | Complexity: Moderate
```

**Use when:**
- You need cross-platform compatibility
- Docker in VM is sufficient
- Performance is important

### Advanced Setup (Layers 1-5)
```
Host → QEMU → VM with KVM → Docker Container → Inner VM
Performance: Poor | Security: Excellent | Complexity: High
```

**Use when:**
- You need maximum isolation
- Testing multi-layer virtualization
- Security is critical (sandbox within sandbox within sandbox)

## Inside the VM

Once connected via SSH:

```bash
# Check Docker
docker --version
docker ps

# Check KVM support
kvm-ok

# Check libvirt
libvirtd --version

# View NEXUS logs
tail -f ~/.nexus/logs/*.log

# Run Docker container
docker run -d --name test alpine sleep 3600
```

## Configuration

The VM is configured in `~/.nexus-nested-vm/configs/user-data.yaml`:

```yaml
packages:
  - docker.io          # Container runtime
  - qemu-system-arm64  # ARM64 KVM hypervisor
  - libvirt-daemon     # Libvirt for VM management
  - libvirt-clients

runcmd:
  - usermod -aG docker ubuntu
  - systemctl start docker
  - systemctl enable docker
  - systemctl start libvirtd
```

To modify: Edit the file, delete the QCOW2 disk, and re-run the init script.

## Nested VM Performance

QEMU on Apple Silicon M1:
- Single VM: 10-20% overhead vs native
- VM with container: 20-30% overhead
- Nested VMs: 40-50% overhead

**Recommended**: Use only 1-2 nesting levels. Triple nesting is more for experimentation than production.

## Networking

Port forwarding (host → VM):
- SSH: `localhost:2222` → VM port 22
- HTTP: `localhost:8080` → VM port 80
- HTTPS: `localhost:8443` → VM port 443

To add custom ports, edit `start-nested-vm.sh`:
```bash
-net user,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::9000-:9000
```

## Storage

The VM uses QCOW2 copy-on-write disk:
- **Base image**: Ubuntu 24.04 LTS (~2.5GB)
- **Allocated**: 20GB logical size
- **Actual size**: Grows as needed (~5-10GB typical)

Location: `~/.nexus-nested-vm/images/nexus-nested-linux-disk.qcow2`

Resize if needed:
```bash
qemu-img resize ~/.nexus-nested-vm/images/nexus-nested-linux-disk.qcow2 +10G
```

Then inside VM:
```bash
sudo growpart /dev/vda 1
sudo resize2fs /dev/vda1
```

## Stopping the VM

**Graceful shutdown:**
```bash
ssh -p 2222 ubuntu@localhost
sudo poweroff
```

**Force stop:**
Press `Ctrl+A` then `X` in the QEMU terminal

## Troubleshooting

### VM won't start
```bash
# Verify QEMU
qemu-system-aarch64 --version

# Check disk exists
ls -lh ~/.nexus-nested-vm/images/
```

### Slow performance
- Reduce VM resources in `start-nested-vm.sh`
- Monitor host: `top`
- Check Docker: `docker stats`

### SSH connection refused
```bash
# VM might still be booting
sleep 30
ssh -p 2222 ubuntu@localhost

# If still fails, check port forwarding
lsof -i :2222
```

### KVM not available
```bash
ssh -p 2222 ubuntu@localhost
kvm-ok

# Output "KVM acceleration can be used" = ready for nested VMs
```

## Advanced: Running VMs Inside the VM

Inside the nested VM, you can run your own KVM-based VMs:

```bash
# SSH into VM
ssh -p 2222 ubuntu@localhost

# Create a new VM disk
qemu-img create -f qcow2 inner-vm.qcow2 10G

# Start KVM VM (nested)
qemu-system-x86_64 \
  -enable-kvm \
  -m 1G \
  -smp 1 \
  -drive file=inner-vm.qcow2 \
  -nographic
```

⚠️ **Warning**: Performance will be significantly degraded (40-50% of host).

## Platform-Specific Notes

### macOS (Apple Silicon M1/M2)
- ✅ Fully supported via QEMU with Apple Virtualization Framework acceleration
- Uses ARM64 Ubuntu image
- Performance: ~85% of native

### Linux
- ✅ Native KVM support
- Can use x86_64 or ARM64 images
- Performance: ~90% of native

### Windows
- ✅ QEMU supported
- Download from: https://www.qemu.org/download/#windows
- Performance: ~80% of native

## Next Steps

1. Run: `./scripts/init-qemu-nested-vm.sh`
2. Wait for installation
3. Start VM: `~/.nexus-nested-vm/start-nested-vm.sh`
4. Connect: `~/.nexus-nested-vm/connect-ssh.sh`
5. Deploy NEXUS: Docker pull + run containers inside

---

For more details on NEXUS architecture, see [ARCHITECTURE.md](../ARCHITECTURE.md).
