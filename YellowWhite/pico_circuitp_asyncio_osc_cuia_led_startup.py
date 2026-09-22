import time
import os
import wifi
import socketpool
import microosc
import asyncio
import rotaryio
import digitalio
import board
import pwmio

VERSION = 2.003

# ====================== HELPER ======================
def get_float(key, default):
    val = os.getenv(key)
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

# ====================== CONFIG ======================
UDP_HOST = os.getenv("OSC_HOST", "192.168.0.5")
UDP_PORT = int(os.getenv("OSC_PORT", "1370"))

ssid = os.getenv("WIFI_SSID")
password = os.getenv("WIFI_PASSWORD")

FLASH_BRIGHTNESS = 1
SHORT_THRESHOLD = get_float("BUTTON_SHORT_THRESHOLD_SEC", 0.30)
BOLD_THRESHOLD = get_float("BUTTON_BOLD_THRESHOLD_SEC", 1.00)
LONG_THRESHOLD = get_float("BUTTON_LONG_THRESHOLD_SEC", 2.00)
FLASH_DURATION = get_float("LED_FLASH_DURATION_SEC", 0.40)
ROT_FLASH_DURATION = get_float("LED_ROT_FLASH_DURATION_SEC", 0.12)
POLL_INTERVAL = get_float("POLL_INTERVAL_SEC", 0.008)

# ====================== RGB LED SETUP ======================
RED = pwmio.PWMOut(getattr(board, os.getenv("LED_RED_PIN", "GP9")), frequency=1000, duty_cycle=0)
GREEN = pwmio.PWMOut(getattr(board, os.getenv("LED_GREEN_PIN", "GP10")), frequency=1000, duty_cycle=0)
BLUE = pwmio.PWMOut(getattr(board, os.getenv("LED_BLUE_PIN", "GP11")), frequency=1000, duty_cycle=0)

def set_rgb(r, g, b):
    RED.duty_cycle = min(65535, max(0, int(round(r))))
    GREEN.duty_cycle = min(65535, max(0, int(round(g))))
    BLUE.duty_cycle = min(65535, max(0, int(round(b))))


# ====================== STARTUP + READY PULSE ======================
async def ready_pulse_task():
    """Gentle white pulse every second to show the device is powered on"""
    brightness = 0.01
    while True:
        set_rgb(65535 * brightness, 65535 * brightness, 65535 * brightness)
        await asyncio.sleep(0.01)   # on time
        set_rgb(0, 0, 0)
        await asyncio.sleep(0.99)   # off time → ~1 second cycle


def initial_startup_sequence():
    """One-time boot animation"""
    print("Running initial LED startup sequence...")

    brightness = 0.01

    # Short white pulse
    set_rgb(65535 * brightness, 65535 * brightness, 65535 * brightness)
    time.sleep(0.25)
    set_rgb(0, 0, 0)
    time.sleep(0.12)

    # Color cycle
    colors = [
        (65535, 0, 0),      # Red
        (0, 65535, 0),      # Green
        (0, 0, 65535),      # Blue
        (65535, 65535, 0),  # Yellow
        (65535, 0, 65535),  # Magenta
    ]
    for r, g, b in colors:
        set_rgb(r * brightness, g * brightness, b * brightness)
        time.sleep(0.16)
        set_rgb(0, 0, 0)
        time.sleep(0.08)

    print("Initial startup done → Ready pulse active.")


# ====================== ENCODER FLASH ======================
ENCODER_FLASH_COLORS = [
    (65535, 0, 0), (0, 40000, 0), (0, 0, 65535), (65535, 0, 65535)
]

async def flash_led_for_encoder(enc_idx: int, duration=FLASH_DURATION, brightness=FLASH_BRIGHTNESS):
    if not (0 <= enc_idx <= 3):
        return
    brightness = brightness / 100.0
    r, g, b = ENCODER_FLASH_COLORS[enc_idx]
    set_rgb(r * brightness, g * brightness, b * brightness)
    await asyncio.sleep(duration)
    set_rgb(0, 0, 0)


# ── ButtonBase ───────────────────────────────────────────────────────────────
class ButtonBase:
    def __init__(self, idx, name, pin_name):
        self.idx = idx
        self.name = name
        sw_pin = getattr(board, pin_name)
        self.switch = digitalio.DigitalInOut(sw_pin)
        self.switch.switch_to_input(pull=digitalio.Pull.UP)
        self.press_start = None
        self.long_sent = False
        self.last_value = self.switch.value

    def _send_action(self, action_type: str):
        try:
            msg = microosc.OscMsg("/CUIA/ZYNSWITCH", [self.idx, action_type], ("i", "s"))
            osc_client.send(msg)
            print(f"ZYNSWITCH {self.name} ({self.idx}): {action_type}")
            if 0 <= self.idx <= 3:
                asyncio.create_task(flash_led_for_encoder(self.idx))
        except OSError as e:
            print(f"OSC send failed: {e}")

    def check_button(self, now: float):
        pressed = not self.switch.value
        if pressed != self.last_value:
            self.last_value = pressed

        if pressed:
            if self.press_start is None:
                self.press_start = now
                self.long_sent = False
                self._send_action("P")
            elif not self.long_sent and (now - self.press_start) >= LONG_THRESHOLD:
                self._send_action("L")
                self.long_sent = True
        else:
            if self.press_start is not None:
                duration = now - self.press_start
                if duration < SHORT_THRESHOLD:
                    self._send_action("S")
                elif duration < LONG_THRESHOLD:
                    self._send_action("B")
                else:
                    self._send_action("L")
                self.press_start = None
                self.long_sent = False


# ── Encoder ─────────────────────────────────────────────────────────────────
class Encoder(ButtonBase):
    def __init__(self, idx, name, switch_pin, a_pin_name, b_pin_name):
        super().__init__(idx, name, switch_pin)
        a = getattr(board, a_pin_name)
        b = getattr(board, b_pin_name)
        self.encoder = rotaryio.IncrementalEncoder(a, b)
        self.last_pos = self.encoder.position

    async def monitor(self):
        while True:
            now = time.monotonic()
            pos = self.encoder.position
            if pos != self.last_pos:
                delta = pos - self.last_pos
                try:
                    msg = microosc.OscMsg("/CUIA/ZYNPOT", [self.idx, delta], ("i", "i"))
                    osc_client.send(msg)
                    print(f"ZYNPOT {self.name} ({self.idx}): {delta:+d}")
                    asyncio.create_task(flash_led_for_encoder(self.idx, ROT_FLASH_DURATION))
                except OSError as e:
                    print(f"ZYNPOT send failed: {e}")
                self.last_pos = pos

            self.check_button(now)
            await asyncio.sleep(POLL_INTERVAL)


# ── SimpleSwitch ────────────────────────────────────────────────────────────
class SimpleSwitch(ButtonBase):
    async def monitor(self):
        while True:
            now = time.monotonic()
            self.check_button(now)
            await asyncio.sleep(POLL_INTERVAL)


# ====================== MAIN ======================
print(f"Starting pico_circuitp_asyncio_osc_cuia_led.py v{VERSION}")

print("Connecting to WiFi:", ssid)
wifi.radio.connect(ssid, password)
print("My IP address:", wifi.radio.ipv4_address)

socket_pool = socketpool.SocketPool(wifi.radio)
osc_client = microosc.OSCClient(socket_pool, UDP_HOST, UDP_PORT)
print("OSC client ready →", UDP_HOST, UDP_PORT)

# Build hardware objects
encoders = []
for i in range(4):
    prefix = f"ENCODER_{i}_"
    name = os.getenv(prefix + "NAME")
    sw = os.getenv(prefix + "SWITCH")
    a = os.getenv(prefix + "A")
    b = os.getenv(prefix + "B")
    if not all([name, sw, a, b]):
        print(f"Warning: Encoder {i} config incomplete — skipping")
        continue
    encoders.append(Encoder(i, name, sw, a, b))

simple_switches = []
for i in range(4, 8):
    prefix = f"SWITCH_{i}_"
    name = os.getenv(prefix + "NAME")
    pin = os.getenv(prefix + "PIN")
    if not all([name, pin]):
        print(f"Warning: Switch {i} config incomplete — skipping")
        continue
    simple_switches.append(SimpleSwitch(i, name, pin))

# === STARTUP ===
initial_startup_sequence()

print("Starting main loop with ready pulse...")
try:
    async def main():
        tasks = [asyncio.create_task(enc.monitor()) for enc in encoders]
        tasks += [asyncio.create_task(sw.monitor()) for sw in simple_switches]
        tasks.append(asyncio.create_task(ready_pulse_task()))   # Continuous ready pulse

        await asyncio.gather(*tasks)

    asyncio.run(main())

except KeyboardInterrupt:
    print("\nStopped by user")
except Exception as e:
    print("Error:", e)
finally:
    set_rgb(0, 0, 0)
    print("LEDs off")