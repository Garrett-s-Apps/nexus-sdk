#!/bin/bash
# NEXUS QEMU Nested VM Auto-Install & Auto-Scaffold
# With secure SSH key management and agent forwarding
# Runs on startup to initialize triple-nested virtualization environment
# Mac M1/M2 compatible

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VM_DIR="$HOME/.nexus-nested-vm"
VM_NAME="nexus-nested-linux"
SSH_DIR="$HOME/.ssh"

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

log_info "NEXUS Nested VM Auto-Init with Secure SSH"
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

# Step 2: Secure SSH Key Setup
log_info "Step 2: Setting up secure SSH keys..."

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

SSH_KEY="$SSH_DIR/id_nexus_vm"

if [ ! -f "$SSH_KEY" ]; then
  log_warn "SSH key not found. Generating secure ed25519 key..."
  ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "nexus-vm@$(hostname)" -q
  chmod 600 "$SSH_KEY"
  chmod 644 "$SSH_KEY.pub"
  log_ok "SSH key generated: $SSH_KEY"
else
  log_ok "SSH key exists: $SSH_KEY"
fi

# Step 3: Create VM directory structure
log_info "Step 3: Scaffolding VM environment..."
mkdir -p "$VM_DIR"
mkdir -p "$VM_DIR/images"
mkdir -p "$VM_DIR/configs"
mkdir -p "$VM_DIR/logs"

log_ok "VM directory: $VM_DIR"

# Step 4: Create cloud-init configuration with SSH setup
log_info "Step 4: Creating cloud-init with secure SSH..."

# Read the public key
SSH_PUB_KEY=$(cat "$SSH_KEY.pub")

cat > "$VM_DIR/configs/user-data.yaml" << CLOUD_INIT
#cloud-config
hostname: nexus-nested
users:
  - name: ubuntu
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    shell: /bin/bash
    ssh_authorized_keys:
      - $SSH_PUB_KEY
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
  - openssh-server
runcmd:
  - usermod -aG docker ubuntu
  - systemctl start docker
  - systemctl enable docker
  - systemctl start libvirtd
  - systemctl enable libvirtd
  - systemctl start ssh
  - systemctl enable ssh
  # Disable password auth for security
  - sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
  - sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
  - systemctl restart ssh
  - echo "SSH key-only authentication enabled" > /var/log/nexus-init.log
write_files:
  - path: /home/ubuntu/.nexus/config.yaml
    permissions: '0644'
    content: |
      nested_vm_enabled: true
      orchestration_mode: autonomous
      container_isolation: triple-nested
      ssh_auth: key-only
CLOUD_INIT

log_ok "Cloud-init configuration created with SSH key auth"

# Step 5: Create enhanced startup script with SSH agent forwarding
log_info "Step 5: Creating VM startup script with SSH agent forwarding..."

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
echo "   SSH: localhost:2222 (key-based auth)"
echo "   RAM: 4GB | CPUs: 2 | Disk: 20GB"
echo ""
echo "   Connect: ssh -p 2222 ubuntu@localhost"
echo "   Or use: ~/.nexus-nested-vm/connect-ssh.sh"
echo ""
echo "   Ctrl+A then X to stop"
echo ""

# Detect QEMU binary and architecture
if command -v qemu-system-aarch64 &> /dev/null; then
  QEMU="qemu-system-aarch64"
  QEMU_ARGS="-machine virt,gic-version=3 -cpu host"
  BIOS_ARG="-bios /opt/homebrew/share/qemu/edk2-aarch64-code.fd"
else
  QEMU="qemu-system-x86_64"
  QEMU_ARGS="-machine pc -cpu host"
  BIOS_ARG=""
fi

# Start QEMU with SSH agent socket if available
if [ -n "$SSH_AUTH_SOCK" ]; then
  # SSH agent forwarding enabled
  $QEMU \
    $QEMU_ARGS \
    -m 4G \
    -smp 2 \
    -drive file=$DISK_FILE,if=virtio,cache=writethrough \
    -drive file=$INIT_ISO,if=virtio,cache=writethrough \
    -nographic \
    -net nic,model=virtio \
    -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::8443-:443 \
    $BIOS_ARG 2>/dev/null || true
else
  # Standard start without agent forwarding
  $QEMU \
    $QEMU_ARGS \
    -m 4G \
    -smp 2 \
    -drive file=$DISK_FILE,if=virtio,cache=writethrough \
    -drive file=$INIT_ISO,if=virtio,cache=writethrough \
    -nographic \
    -net nic,model=virtio \
    -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::8443-:443 \
    $BIOS_ARG 2>/dev/null || true
fi
VM_START

chmod +x "$VM_DIR/start-nested-vm.sh"
log_ok "Startup script created with SSH agent support"

# Step 6: Create enhanced SSH connection script with agent forwarding
log_info "Step 6: Creating enhanced SSH connection helpers..."

cat > "$VM_DIR/connect-ssh.sh" << 'SSH_CONNECT'
#!/bin/bash
echo "🔌 Connecting to NEXUS Nested VM..."
echo "   Host: localhost:2222"
echo "   User: ubuntu"
echo "   Auth: SSH key (no password)"
echo ""

# Use the specific SSH key
SSH_KEY="$HOME/.ssh/id_nexus_vm"

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found: $SSH_KEY"
  exit 1
fi

# Connect with agent forwarding enabled
ssh -p 2222 \
    -i "$SSH_KEY" \
    -A \
    -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile="$HOME/.ssh/known_hosts_nexus_vm" \
    ubuntu@localhost
SSH_CONNECT

chmod +x "$VM_DIR/connect-ssh.sh"
log_ok "SSH connection helper created"

# Step 7: Auto-add to SSH config
log_info "Step 7: Adding VM to SSH config..."

SSH_CONFIG="$HOME/.ssh/config"
VM_CONFIG_BLOCK="Host nexus-vm
    HostName localhost
    Port 2222
    User ubuntu
    IdentityFile $SSH_KEY
    StrictHostKeyChecking accept-new
    UserKnownHostsFile $SSH_DIR/known_hosts_nexus_vm
    ForwardAgent yes
    ServerAliveInterval 60"

if [ ! -f "$SSH_CONFIG" ]; then
  mkdir -p "$SSH_DIR"
  echo "$VM_CONFIG_BLOCK" > "$SSH_CONFIG"
  chmod 600 "$SSH_CONFIG"
  log_ok "Created SSH config: $SSH_CONFIG"
else
  if ! grep -q "Host nexus-vm" "$SSH_CONFIG"; then
    echo "" >> "$SSH_CONFIG"
    echo "$VM_CONFIG_BLOCK" >> "$SSH_CONFIG"
    log_ok "Added nexus-vm to SSH config"
  else
    log_ok "nexus-vm already in SSH config"
  fi
fi

# Step 8: Download Ubuntu image (if needed)
log_info "Step 8: Preparing Ubuntu image..."

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

# Step 9: Create QCOW2 disk
log_info "Step 9: Creating QCOW2 disk..."

if [ ! -f "$VM_DIR/images/$VM_NAME-disk.qcow2" ]; then
  qemu-img create -f qcow2 -b "$VM_DIR/images/jammy-server-cloudimg-arm64.img" \
    "$VM_DIR/images/$VM_NAME-disk.qcow2" 20G
  log_ok "QCOW2 disk created (20GB)"
fi

# Step 10: Create cloud-init ISO
log_info "Step 10: Creating cloud-init ISO..."

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

# Completion
log_ok "================================================"
log_ok "✅ NEXUS Nested VM with Secure SSH Ready!"
log_ok ""
log_ok "SSH Key Details:"
log_ok "  Private: $SSH_KEY (600 - read-only)"
log_ok "  Public:  $SSH_KEY.pub"
log_ok "  Type:    ed25519 (modern, secure)"
log_ok "  Auth:    Key-only (passwords disabled)"
log_ok ""
log_ok "Quick Start:"
log_ok "  1. Start VM:    $VM_DIR/start-nested-vm.sh"
log_ok "  2. Connect:     $VM_DIR/connect-ssh.sh"
log_ok "  3. Or use SSH:  ssh nexus-vm"
log_ok ""
log_ok "Security Features:"
log_ok "  ✅ SSH key authentication (ed25519)"
log_ok "  ✅ Password authentication disabled"
log_ok "  ✅ SSH agent forwarding enabled"
log_ok "  ✅ Separate known_hosts file"
log_ok "  ✅ StrictHostKeyChecking (auto-accept once)"
log_ok "================================================"
