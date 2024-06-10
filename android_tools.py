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
                "required": ["x", "y", "direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "back",
            "description": "Go back",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]