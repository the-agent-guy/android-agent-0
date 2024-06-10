from prompts import AUTOMATON_SYSTEM_PROMPT, AUTOMATON_TASK_PROMPT, AUTOMATON_HISTORY_INPUT_PROMPT, AUTOMATON_SCREENSHOT_INPUT_PROMPT, AUTOMATON_SCREENSHOT_INPUT_PROMPT_PARTIAL
from action_types import Tap, Text, LongPress, Swipe, Back
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


class GPT4oNaiveVisionAgent:
    def __init__(self):
        self.client = OpenAI()
        # rolling buffer that contains last 5 screenshots and actions
        self.history_buffer = []

    # image path to base64 string
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    # resizes base64 image
    def resize_image(self, image_base64, scale):
        buffer = io.BytesIO()
        imgdata = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(imgdata))
        new_img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
        new_img = new_img.convert("RGB")
        new_img.save(buffer, format="PNG")
        # new_img.save("temp.png", format="PNG")
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return image
    
    def get_image_size(self, image_base64):
        imgdata = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(imgdata))
        return img.size
    
    # needs to return base64 chunk and size in [l, t, r, b]
    def get_chunks(self, image_base64, w_chunks=2, h_chunks=4):
        chunks = []
        img_w, img_h = self.get_image_size(image_base64)
        chunk_w = img_w // w_chunks 
        chunk_h = img_h // h_chunks 
        for h in range(h_chunks):
            for w in range(w_chunks):
                # get bbox
                current_chunk_l = w * chunk_w
                current_chunk_t = h * chunk_h
                current_chunk_r = min(current_chunk_l + chunk_w, img_w)
                current_chunk_b = min(current_chunk_t + chunk_h, img_h)

                # get and crop image from base64
                imgdata = base64.b64decode(image_base64)
                img = Image.open(io.BytesIO(imgdata))
                image_chunk = img.crop((current_chunk_l, current_chunk_t, current_chunk_r, current_chunk_b))

                # to base64
                buffer = io.BytesIO()
                image_chunk = image_chunk.convert("RGB")
                image_chunk.save(buffer, format="PNG")
                image_chunk_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                # image_chunk_base64 = self.resize_image(image_chunk_base64, 0.3)
                chunks.append((image_chunk_base64, [current_chunk_l, current_chunk_t, current_chunk_r, current_chunk_b]))
        
        return chunks
    
    # input messages showing downsampled image + chunks with corresponding coordinate bounds
    def prepare_screenshot_input(self, screenshot_path):
        screenshot_input = []
        # full screenshot downsampled
        screenshot_base64 = self.encode_image(screenshot_path)
        # we get size before resizing because model needs to take coordinate actions on the original screen
        screenshot_size = self.get_image_size(screenshot_base64)
        # screenshot_base64 = self.resize_image(screenshot_base64, 0.4)
        screenshot_input.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": AUTOMATON_SCREENSHOT_INPUT_PROMPT.format(
                            x = screenshot_size[0], y=screenshot_size[1]
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_base64}"
                        },
                    },
                ],
            }
        )

        screenshot_chunks = self.get_chunks(screenshot_base64)
        for screenshot_chunk_base64, [l, t, r, b] in screenshot_chunks:
            # print(AUTOMATON_SCREENSHOT_INPUT_PROMPT_PARTIAL.format(x1=l, y1=t, x2=r, y2=b))
            screenshot_input.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": AUTOMATON_SCREENSHOT_INPUT_PROMPT_PARTIAL.format(
                                x1=l, y1=t, x2=r, y2=b
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{screenshot_chunk_base64}"
                            },
                        },
                    ],
                }
            )

        return screenshot_input

    # input message showing prev downsampled screenshots + actions
    def prepare_history_input(self):
        # print(self.history_buffer)
        history_input = []
        for i in range(len(self.history_buffer)):
            screenshot_path = self.history_buffer[i].screenshot
            actions = self.history_buffer[i].actions
            history_input.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": AUTOMATON_HISTORY_INPUT_PROMPT.format(
                                i=len(self.history_buffer) - i, action=str(actions)
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self.resize_image(self.encode_image(screenshot_path), 0.2)}"
                            },
                        },
                    ],
                }
            )
        return history_input


    def prepare_messages(self, screenshot_path, task):

        # system and task messages
        messages = []
        messages.append({"role": "user", "content": AUTOMATON_SYSTEM_PROMPT})
        messages.append(
            {"role": "user", "content": AUTOMATON_TASK_PROMPT.format(task=task)}
        )

        # messages describing current system state
        messages += self.prepare_history_input()
        messages += self.prepare_screenshot_input(screenshot_path)

        return messages

    def __call__(self, screenshot_path, task):

        messages = self.prepare_messages(screenshot_path, task)

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
                elif function_name == "back":
                    actions.append(Back())
        
        # TODO: this is a temp thing to fix gmail issue, should remove later
        actions = actions[:1]
        
        # update history buffer
        self.history_buffer.append(HistoryItem(screenshot=screenshot_path, actions=actions))
        self.history_buffer = self.history_buffer[-5:]

        return actions