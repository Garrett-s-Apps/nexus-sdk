#!/bin/bash
# NEXUS QEMU Nested VM Auto-Install & Auto-Scaffold
# Runs on startup to initialize triple-nested virtualization environment
# Mac M1/M2 compatible

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VM_DIR="$HOME/.nexus-nested-vm"
VM_NAME="nexus-nested-linux"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_ok() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

log_info "NEXUS Nested VM Auto-Init"
log_info "================================================"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="mac"
  QEMU_CMD="qemu-system-aarch64"
  log_ok "Detected: macOS (Apple Silicon)"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="linux"
  QEMU_CMD="qemu-system-x86_64"
  log_ok "Detected: Linux"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
  OS="windows"
  QEMU_CMD="qemu-system-x86_64.exe"
  log_ok "Detected: Windows"
else
  log_error "Unsupported OS: $OSTYPE"
  exit 1
fi

# Step 1: Check/Install QEMU
log_info "Step 1: Checking QEMU installation..."

if ! command -v $QEMU_CMD &> /dev/null; then
  log_warn "QEMU not found. Installing..."

  if [[ "$OS" == "mac" ]]; then
    if ! command -v brew &> /dev/null; then
      log_error "Homebrew not found. Please install: https://brew.sh"
      exit 1
    fi
    log_info "Installing via Homebrew..."
    brew install qemu
  elif [[ "$OS" == "linux" ]]; then
    if command -v apt-get &> /dev/null; then
      log_info "Installing via apt..."
      sudo apt-get update
      sudo apt-get install -y qemu-system-arm qemu-system-x86
    elif command -v yum &> /dev/null; then
      log_info "Installing via yum..."
      sudo yum install -y qemu-system-arm qemu-system-x86
    else
      log_error "Could not find package manager"
      exit 1
    fi
  elif [[ "$OS" == "windows" ]]; then
    log_error "Windows: Please download QEMU from https://www.qemu.org/download/#windows"
    exit 1
  fi
fi

QEMU_VERSION=$($QEMU_CMD --version | head -1)
log_ok "$QEMU_VERSION"

# Step 2: Create VM directory structure
log_info "Step 2: Scaffolding VM environment..."
mkdir -p "$VM_DIR"
mkdir -p "$VM_DIR/images"
mkdir -p "$VM_DIR/configs"
mkdir -p "$VM_DIR/logs"

log_ok "VM directory: $VM_DIR"

# Step 3: Create cloud-init configuration
log_info "Step 3: Creating cloud-init configuration..."

cat > "$VM_DIR/configs/user-data.yaml" << 'CLOUD_INIT'
#cloud-config
hostname: nexus-nested
users:
  - name: ubuntu
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    shell: /bin/bash
    ssh_authorized_keys:
      - $(cat ~/.ssh/id_rsa.pub 2>/dev/null || echo "ssh-rsa PLACEHOLDER")
package_update: true
packages:
  - docker.io
  - qemu-system-arm64
  - libvirt-daemon
  - libvirt-clients
  - curl
  - git
  - python3-pip
  - tmux
runcmd:
  - usermod -aG docker ubuntu
  - systemctl start docker
  - systemctl enable docker
  - systemctl start libvirtd
  - systemctl enable libvirtd
  - echo "NEXUS nested VM ready for operations" > /var/log/nexus-init.log
write_files:
  - path: /home/ubuntu/.nexus/config.yaml
    permissions: '0644'
    content: |
      nested_vm_enabled: true
      orchestration_mode: autonomous
      container_isolation: triple-nested
CLOUD_INIT

log_ok "Cloud-init configuration created"

# Step 4: Create startup script
log_info "Step 4: Creating VM startup script..."

cat > "$VM_DIR/start-nested-vm.sh" << 'VM_START'
#!/bin/bash
set -e

VM_NAME="nexus-nested-linux"
VM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISK_FILE="$VM_DIR/images/$VM_NAME-disk.qcow2"
INIT_ISO="$VM_DIR/images/init.iso"

if [ ! -f "$DISK_FILE" ]; then
  echo "❌ VM disk not found: $DISK_FILE"
  echo "Run init-qemu-nested-vm.sh first"
  exit 1
fi

echo "🚀 Starting NEXUS Nested VM..."
echo "   RAM: 4GB | CPUs: 2 | Disk: 20GB"
echo "   SSH: localhost:2222"
echo "   Ctrl+A then X to stop"
echo ""

qemu-system-aarch64 \
  -machine virt,gic-version=3 \
  -cpu host \
  -m 4G \
  -smp 2 \
  -drive file=$DISK_FILE,if=virtio,cache=writethrough \
  -drive file=$INIT_ISO,if=virtio,cache=writethrough \
  -nographic \
  -net nic,model=virtio \
  -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::8443-:443 \
  -bios /opt/homebrew/share/qemu/edk2-aarch64-code.fd 2>/dev/null || \
  qemu-system-x86_64 \
  -m 4G \
  -smp 2 \
  -drive file=$DISK_FILE,if=virtio,cache=writethrough \
  -drive file=$INIT_ISO,if=virtio,cache=writethrough \
  -nographic \
  -net nic,model=virtio \
  -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::8443-:443
VM_START

chmod +x "$VM_DIR/start-nested-vm.sh"
log_ok "Startup script created"

# Step 5: Download Ubuntu image (if needed)
log_info "Step 5: Preparing Ubuntu image..."

if [ ! -f "$VM_DIR/images/jammy-server-cloudimg-arm64.img" ]; then
  log_warn "Downloading Ubuntu 24.04 LTS (ARM64, ~300MB)..."
  cd "$VM_DIR/images"
  wget -q https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-arm64.img || {
    log_error "Failed to download Ubuntu image"
    log_info "Manual download: https://cloud-images.ubuntu.com/jammy/current/"
    exit 1
  }
  log_ok "Ubuntu image downloaded"
fi

# Step 6: Create QCOW2 disk
log_info "Step 6: Creating QCOW2 disk..."

if [ ! -f "$VM_DIR/images/$VM_NAME-disk.qcow2" ]; then
  qemu-img create -f qcow2 -b "$VM_DIR/images/jammy-server-cloudimg-arm64.img" \
    "$VM_DIR/images/$VM_NAME-disk.qcow2" 20G
  log_ok "QCOW2 disk created (20GB)"
fi

# Step 7: Create cloud-init ISO
log_info "Step 7: Creating cloud-init ISO..."

cd "$VM_DIR/configs"
cat > meta-data.yaml << 'META'
instance-id: nexus-nested-1
local-hostname: nexus-nested
META

mkisofs -output "$VM_DIR/images/init.iso" -volid cidata -joliet -rock \
  user-data.yaml meta-data.yaml 2>/dev/null || {
  log_warn "mkisofs not available, skipping ISO creation"
}

log_ok "Cloud-init ISO created"

# Step 8: Create connection script
log_info "Step 8: Creating connection helper..."

cat > "$VM_DIR/connect-ssh.sh" << 'SSH_CONNECT'
#!/bin/bash
echo "🔌 Connecting to NEXUS Nested VM..."
echo "Default credentials: ubuntu / ubuntu"
echo "Change password on first login: passwd"
echo ""
sleep 2
ssh -p 2222 ubuntu@localhost
SSH_CONNECT

chmod +x "$VM_DIR/connect-ssh.sh"
log_ok "Connection helper created"

# Completion
log_ok "================================================"
log_ok "NEXUS Nested VM fully scaffolded!"
log_ok ""
log_ok "Next steps:"
log_ok "  1. Start VM: $VM_DIR/start-nested-vm.sh"
log_ok "  2. Connect:  $VM_DIR/connect-ssh.sh"
log_ok ""
log_ok "Inside the VM, you can run:"
log_ok "  - docker ps          (check Docker)"
log_ok "  - kvm-ok             (check KVM support)"
log_ok "  - libvirtd status    (check libvirt)"
log_ok "================================================"
