import os
import subprocess
from action_types import Tap, Text, LongPress, Swipe, Back
import xml.etree.ElementTree as ET


ANDROID_SCREENSHOT_DIR = "/sdcard"
ANDROID_XML_DIR = "/sdcard"
SCREENSHOT_SAVE_DIR = "./screenshots"
XML_SAVE_DIR = "./xml"

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


class AndroidElement:
    def __init__(self, uid, bbox, attrib, extra):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib
        self.extra = extra

def traverse_xml(xml_path):

    def get_id_from_element(elem):
        bounds = elem.attrib["bounds"][1:-1].split("][")
        x1, y1 = map(int, bounds[0].split(","))
        x2, y2 = map(int, bounds[1].split(","))
        elem_w, elem_h = x2 - x1, y2 - y1
        if "resource-id" in elem.attrib and elem.attrib["resource-id"]:
            elem_id = elem.attrib["resource-id"].replace(":", ".").replace("/", "_")
        else:
            elem_id = f"{elem.attrib['class']}_{elem_w}_{elem_h}"
        if "content-desc" in elem.attrib and elem.attrib["content-desc"] and len(elem.attrib["content-desc"]) < 20:
            content_desc = elem.attrib['content-desc'].replace("/", "_").replace(" ", "").replace(":", "_")
            elem_id += f"_{content_desc}"
        return elem_id

    path = []
    elem_list = []
    for event, elem in ET.iterparse(xml_path, ['start', 'end']):
        if event == 'start':
            path.append(elem)
            for attrib in ["clickable", "focusable"]:
                if attrib in elem.attrib and elem.attrib[attrib] == "true":
                    parent_prefix = ""
                    if len(path) > 1:
                        parent_prefix = get_id_from_element(path[-2])
                    bounds = elem.attrib["bounds"][1:-1].split("][")
                    x1, y1 = map(int, bounds[0].split(","))
                    x2, y2 = map(int, bounds[1].split(","))
                    center = (x1 + x2) // 2, (y1 + y2) // 2
                    elem_id = get_id_from_element(elem)
                    if parent_prefix:
                        elem_id = parent_prefix + "_" + elem_id
                    close = False
                    for e in elem_list:
                        bbox = e.bbox
                        center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                        dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                        if dist <= 30:
                            close = True
                            break
                    if not close:
                        extra = ""
                        if "focused" in elem.attrib and elem.attrib["focused"] != "false":
                            extra += " focused: " + elem.attrib["focused"]
                        if "content-desc" in elem.attrib and elem.attrib["content-desc"] != "":
                            extra += " description: " + elem.attrib["content-desc"]
                        if "text" in elem.attrib and elem.attrib["text"] != "":
                            extra += " text: " + elem.attrib["text"]
                        if "resource-id" in elem.attrib and elem.attrib["resource-id"] != "":
                            extra += " resource-id: " + elem.attrib["resource-id"]
                        elem_list.append(AndroidElement(elem_id, ((x1, y1), (x2, y2)), attrib, extra))

        if event == 'end':
            path.pop()
    return elem_list

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
    
    def get_xml(self, i):
        dump_command = f"adb -s {self.device} shell uiautomator dump " \
                       f"{os.path.join(ANDROID_XML_DIR, str(i) + '.xml').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(ANDROID_XML_DIR, str(i) + '.xml').replace(self.backslash, '/')} " \
                       f"{os.path.join(XML_SAVE_DIR, str(i) + '.xml')}"
        result = adb_execute(dump_command)
        if result != "ERROR":
            result = adb_execute(pull_command)
            if result != "ERROR":
                return os.path.join(XML_SAVE_DIR, str(i) + ".xml")
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
        elif isinstance(action, Back):
            command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
            adb_command(command)