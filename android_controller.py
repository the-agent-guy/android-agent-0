import os
import subprocess
from action_types import Tap, Text, LongPress, Swipe

ANDROID_SCREENSHOT_DIR = "/sdcard"
SCREENSHOT_SAVE_DIR = "./screenshots"

def adb_execute(command):
    result = subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        print("COMMAND EXECUTION FAILED FOR: {}".format(command))
    return "ERROR"


def list_devices():
    devices = []
    result = adb_execute("adb devices")
    if result != "ERROR":
        devices = result.split("\n")[1:]
        devices = [d.split()[0] for d in devices]
    return devices

class AndroidController:
    def __init__(self, device):
        self.backslash = "\\"
        self.device = device

    def get_screenshot(self, i):
        cap_command = (
            f"adb -s {self.device} shell screencap -p "
            f"{os.path.join(ANDROID_SCREENSHOT_DIR, str(i) + '.png').replace(self.backslash, '/')}"
        )
        pull_command = (
            f"adb -s {self.device} pull "
            f"{os.path.join(ANDROID_SCREENSHOT_DIR, str(i) + '.png').replace(self.backslash, '/')} "
            f"{os.path.join(SCREENSHOT_SAVE_DIR, str(i) + '.png')}"
        )
        result = adb_execute(cap_command)
        if result != "ERROR":
            result = adb_execute(pull_command)
            if result != "ERROR":
                return os.path.join(SCREENSHOT_SAVE_DIR, str(i) + ".png")
            return result
        return result

    def get_device_size(self):
        command = f"adb -s {self.device} shell wm size"
        result = adb_execute(command)
        if result != "ERROR":
            return map(int, result.split(": ")[1].split("x"))
        else:
            return 0, 0

    def action_execute(self, action):
        if isinstance(action, Tap):
            command = f"adb -s {self.device} shell input tap {action.x} {action.y}"
            adb_execute(command)
        elif isinstance(action, Text):
            input_str = action.input_str.replace(" ", "%s")
            input_str = input_str.replace("'", "")
            command = f"adb -s {self.device} shell input text {input_str}"
            adb_execute(command)
        elif isinstance(action, LongPress):
            command = f"adb -s {self.device} shell input swipe {action.x} {action.y} {action.x} {action.y} {1000}"
            adb_execute(command)
        elif isinstance(action, Swipe):
            unit_dist = int(self.width / 10)
            if action.dist == "long":
                unit_dist *= 3
            elif action.dist == "medium":
                unit_dist *= 2
            if action.direction == "up":
                offset = 0, -2 * unit_dist
            elif action.direction == "down":
                offset = 0, 2 * unit_dist
            elif action.direction == "left":
                offset = -1 * unit_dist, 0
            elif action.direction == "right":
                offset = unit_dist, 0
            else:
                return "ERROR"
            duration = 100 if action.quick else 400
            command = f"adb -s {self.device} shell input swipe {action.x} {action.y} {action.x+offset[0]} {action.y+offset[1]} {duration}"
            adb_execute(command)