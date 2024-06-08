from prompts import AUTOMATON_SYSTEM_PROMPT, AUTOMATON_TASK_PROMPT, AUTOMATON_HISTORY_INPUT_PROMPT, AUTOMATON_SCREENSHOT_INPUT_PROMPT
from action_types import Tap, Text, LongPress, Swipe
import base64
import json
from android_tools import android_tools
from openai import OpenAI
from pydantic import BaseModel
from typing import Union
from dotenv import load_dotenv
import io
from PIL import Image

load_dotenv(".env.local")


# image path and action
class HistoryItem(BaseModel):
    screenshot: str 
    actions: list[Union[Tap, Text, LongPress, Swipe]]


class GPT4oAgent:
    def __init__(self):
        self.client = OpenAI()
        # rolling buffer that contains last 5 screenshots and actions
        self.history_buffer = []

    # image path to base64 string
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    # resizes base64 image
    def resize_image(self, image, scale):
        buffer = io.BytesIO()
        imgdata = base64.b64decode(image)
        img = Image.open(io.BytesIO(imgdata))
        new_img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
        new_img.save(buffer, format="PNG")
        new_img.save("temp.png", format="PNG")
        image = base64.b64encode(buffer.getvalue())
        return image
    
    # input messages showing downsampled image + chunks with corresponding coordinate bounds
    def prepare_screenshot_input(self, screenshot):
        pass

    # input message showing prev downsampled screenshots + actions
    def prepare_history_input(self, history_buffer):
        history_input = []
        for i in range(len(self.history_buffer)):
            screenshot, action = self.history_buffer[i]
            history_input.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": AUTOMATON_HISTORY_INPUT_PROMPT.format(
                                i=len(self.history_buffer) - i, action=str(action)
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self.encode_image(screenshot)}"
                            },
                        },
                    ],
                }
            )
        return history_input


    def prepare_messages(self, screenshot, task):

        # system and task messages
        messages = []
        messages.append({"role": "user", "content": AUTOMATON_SYSTEM_PROMPT})
        messages.append(
            {"role": "user", "content": AUTOMATON_TASK_PROMPT.format(task=task)}
        )
        # TODO: move into prepare_screenshot_input
        # messages.append(
        #     {
        #         "role": "user",
        #         "content": [
        #             {"type": "text", "text": AUTOMATON_SCREENSHOT_INPUT_PROMPT},
        #             {
        #                 "type": "image_url",
        #                 "image_url": {
        #                     "url": f"data:image/jpeg;base64,{self.encode_image(screenshot)}"
        #                 },
        #             },
        #         ],
        #     }
        # )

        # messages describing current system state
        messages += self.prepare_history_input()
        messages += self.prepare_screenshot_input(screenshot)

        return messages

    def __call__(self, screenshot, task):

        messages = self.prepare_messages(screenshot, task)

        # get response
        response = self.client.chat.completions.create(
            messages=messages, model="gpt-4o", tools=android_tools, tool_choice="auto"
        )
        response_message = response.choices[0].message
        print(response_message)
        tool_calls = response_message.tool_calls
        actions = []

        # execute tool calls
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
        
        # update history buffer
        self.history_buffer.append(HistoryItem(screenshot=screenshot, actions=actions))
        self.history_buffer = self.history_buffer[-5:]

        return actions