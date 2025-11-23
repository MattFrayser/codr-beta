# Firejail security profile for Codr code execution (container-compatible)
# Simplified for Docker/Fly.io environment

# Disable network access
net none

# No D-Bus access
nodbus

# No root access
noroot

# Drop all capabilities
caps.drop all

# Disable shell command history
disable-mnt

# Hide sensitive directories
blacklist /boot
blacklist /media
blacklist /mnt
blacklist /opt
blacklist /run/user
blacklist /srv

# Seccomp filter - block dangerous syscalls
seccomp
seccomp.block-secondary

# Read-only paths (protect system files)
read-only /bin
read-only /lib
read-only /lib64
read-only /usr
read-only /etc
read-only /sbin

# Set nice value (lower priority)
nice 10

# Limit resources
rlimit-cpu 10
rlimit-fsize 100000
rlimit-nproc 10
rlimit-nofile 50

# Timeout (overridden by command-line args)
timeout 00:00:10
