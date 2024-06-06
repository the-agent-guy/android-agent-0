import os
import subprocess
from pydantic import BaseModel
from openai import OpenAI
import base64
import json
from dotenv import load_dotenv

load_dotenv()

ANDROID_SCREENSHOT_DIR = "/sdcard"
SCREENSHOT_SAVE_DIR = "./screenshots"
AUTOMATON_SYSTEM_PROMPT = """**GENERAL**
You are Automaton, a mobile agent whose purpose is to take actions on a mobile ui on behalf of the user. 
**STATE**
You will receive the current state of the system in the form of a screenshot. You may also receive some number of previous screenshots and actions.
**ACTIONS**
You will take actions by making tool calls. You will also explain your actions at each step.
"""
AUTOMATON_TASK_PROMPT = """This overarching task is: {task}"""
AUTOMATON_SCREENSHOT_INPUT_PROMPT = """Here is the screenshot representing the current state of the system (mobile phone ui)"""
AUTOMATON_HISTORY_INPUT_PROMPT = """Here is the screenshot {i} steps ago. The action taken at this step was: {action}"""

android_tools = [
    {
        "type": "function",
        "function": {
            "name": "tap",
            "description": "Carries out a tap action at the specified x, y location",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "The x-coordinate of the point to carry out the action at.",
                    },
                    "y": {
                        "type": "integer",
                        "description": "The y-coordinate of the point to carry out the action at.",
                    },
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "longpress",
            "description": "Carries out a long press action at the specified x, y location",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "The x-coordinate of the point to carry out the action at.",
                    },
                    "y": {
                        "type": "integer",
                        "description": "The y-coordinate of the point to carry out the action at.",
                    },
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "text",
            "description": "Enters the specified text in the current active text box.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_str": {
                        "type": "string",
                        "description": "The text to be entered.",
                    },
                },
                "required": ["input_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "swipe",
            "description": "Carries out a swipe action at the specified x, y location",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "The x-coordinate of the point to carry out the action at.",
                    },
                    "y": {
                        "type": "integer",
                        "description": "The y-coordinate of the point to carry out the action at.",
                    },
                    "direction": {
                        "type": "string",
                        "description": "The direction to swipe in. up, down, left, or right",
                    },
                    "dist": {
                        "type": "string",
                        "description": "The distance to swipe for. medium or long",
                    },
                    "quick": {
                        "type": "boolean",
                        "description": "Whether it should be a quick swipe.",
                    },
                },
                "required": ["x", "y", "direction", "dist", "quick"],
            },
        },
    },
]


class Tap(BaseModel):
    x: int
    y: int


class Text(BaseModel):
    input_str: str


class LongPress(BaseModel):
    x: int
    y: int


class Swipe(BaseModel):
    x: int
    y: int
    direction: str
    dist: str
    quick: bool


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


class GPT4oModel:
    def __init__(self):
        self.client = OpenAI()

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def prepare_messages(self, screenshot, history_buffer, task):
        messages = []
        messages.append({"role": "user", "content": AUTOMATON_SYSTEM_PROMPT})
        messages.append(
            {"role": "user", "content": AUTOMATON_TASK_PROMPT.format(task=task)}
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": AUTOMATON_SCREENSHOT_INPUT_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{self.encode_image(screenshot)}"
                        },
                    },
                ],
            }
        )
        for i in range(
            len(history_buffer) - min(5, len(history_buffer)), len(history_buffer)
        ):
            print(history_buffer[i])
            print(len(history_buffer) - i)
            ss, a = history_buffer[i]
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": AUTOMATON_HISTORY_INPUT_PROMPT.format(
                                i=len(history_buffer) - i, action=str(a)
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self.encode_image(ss)}"
                            },
                        },
                    ],
                }
            )
        return messages

    def __call__(self, screenshot, history_buffer, task):
        messages = self.prepare_messages(screenshot, history_buffer, task)
        response = self.client.chat.completions.create(
            messages=messages, model="gpt-4o", tools=android_tools, tool_choice="auto"
        )
        response_message = response.choices[0].message
        print(response_message)
        tool_calls = response_message.tool_calls
        actions = []
        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                if function_name == "tap":
                    actions.append(
                        Tap(x=function_args.get("x"), y=function_args.get("y"))
                    )
                elif function_name == "longpress":
                    actions.append(
                        LongPress(x=function_args.get("x"), y=function_args.get("y"))
                    )
                elif function_name == "text":
                    actions.append(Text(input_str=function_args.get("input_str")))
                elif function_name == "swipe":
                    actions.append(
                        Swipe(x=function_args.get("x"), y=function_args.get("y")),
                        direction=function_args.get("direction"),
                        dist=function_args.get("dist"),
                        quick=function_args.get("quick"),
                    )
        return actions


class Automaton:
    def __init__(self, controller, model):
        self.controller = controller
        self.model = model
        self.done = True

    def run_task(self, task):
        self.task = task
        self.done = False
        i = 0
        history_buffer = []
        while not self.done:
            screenshot = self.controller.get_screenshot(i)
            print(screenshot)
            actions = self.model(screenshot, history_buffer, self.task)
            for action in actions:
                self.controller.action_execute(action)
            history_buffer.append((screenshot, actions))
            i += 1


def main():

    devices = list_devices()
    assert len(devices) > 0
    if len(devices) == 1:
        device = devices[0]
    else:
        print("Devices: {} \nEnter ID to select Device: ".format(devices))
        device = input()

    print("Enter task to be performed: ")
    task = input()

    controller = AndroidController(device)
    model = GPT4oModel()
    automaton = Automaton(controller, model)
    automaton.run_task(task)


if __name__ == "__main__":
    main()
