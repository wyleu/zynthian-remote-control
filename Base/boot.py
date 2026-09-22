# boot.py - Runs VERY early, before USB enumeration
import supervisor
import os

# Get MACHINE from settings (safe fallback)
machine = "BLUE-GREEN"
try:
    # Simple parse for MACHINE (since boot.py is minimal)
    with open("settings.toml", "r") as f:
        for line in f:
            if line.strip().startswith("MACHINE"):
                machine = line.split("=")[1].strip().strip('"')
                break
except:
    pass

# Set USB Identity (this is what lsusb will see)
supervisor.set_usb_identification(
    manufacturer="Zynremote",
    product=f"Zynremote {machine}",
    vid=0x239A,      # Keep Adafruit VID (recommended)
    pid=0x80C1       # Custom PID
)

print(f"USB Identity: Zynremote {machine}")