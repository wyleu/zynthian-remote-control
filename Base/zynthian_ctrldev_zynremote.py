# /zynthian/zynthian-ui/zyngine/ctrldev/zynthian_ctrldev_zynremote.py

import logging
from zyngine.ctrldev.zynthian_ctrldev_base import ZynthianCtrldevBase

class zynthian_ctrldev_zynremote(ZynthianCtrldevBase):

    dev_id = "ZYNREMOTE"                    # Internal ID
    dev_name = "Zynremote"                  # Human readable

    # Match multiple possible USB/MIDI names (Adafruit prefix included)
    supported_devices = [
        "Zynremote",                        # Clean name
        "Adafruit Zynremote",               # Most common
        "Adafruit Zynremote BLUE-GREEN",
        "Adafruit Zynremote WHITE-YELLOW",
        "Zynremote BLUE-GREEN",
        "Zynremote WHITE-YELLOW"
    ]

    def __init__(self, zynapi, midi_port_name=None):
        super().__init__(zynapi, midi_port_name)
        logging.info(f"Zynremote ctrldev driver loaded for: {midi_port_name}")

    # Add your mappings here later
    def midi_event(self, ev):
        # Handle incoming MIDI from the controller
        pass

    def refresh(self):
        # Send feedback to controller (LED states, etc.)
        pass
    
    
# Example: send beat pulse from Zynthian
import liblo
target = liblo.Address("your-pico-ip", 1371)
liblo.send(target, "/beat")          # or "/transport/beat"