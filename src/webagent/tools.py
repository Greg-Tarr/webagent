TOOLS = [
    {
        "name": "send_msg_to_user",
        "description": "Sends a message to the user. Example: send_msg_to_user('Based on the results of my search, the city was built in 1751.')",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The message text to send to the user"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "report_infeasible",
        "description": "Notifies the user that their instructions are infeasible. Example: report_infeasible('I cannot follow these instructions because there is no email field in this form.')",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "The reason why the instructions are infeasible"}
            },
            "required": ["reason"]
        }
    },
    {
        "name": "noop",
        "description": "Do nothing, and optionally wait for the given time (in milliseconds). Examples: noop() or noop(500)",
        "input_schema": {
            "type": "object",
            "properties": {
                "wait_ms": {"type": "number", "description": "Time to wait in milliseconds", "default": 1000}
            },
            "required": []
        }
    },
    {
        "name": "fill",
        "description": "Fill out a form field. It focuses the element and triggers an input event with the entered text. Works for <input>, <textarea> and [contenteditable] elements. Examples: fill('237', 'example value'), fill('45', 'multi-line\\nexample'), fill('a12', 'example with \"quotes\"')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the element to fill"},
                "value": {"type": "string", "description": "The text value to fill into the element"}
            },
            "required": ["bid", "value"]
        }
    },
    {
        "name": "check",
        "description": "Ensure a checkbox or radio element is checked. Example: check('55')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the checkbox/radio element to check"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "uncheck",
        "description": "Ensure a checkbox or radio element is unchecked. Example: uncheck('a5289')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the checkbox/radio element to uncheck"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "select_option",
        "description": "Select one or multiple options in a <select> element. You can specify option value or label to select. Examples: select_option('a48', 'blue'), select_option('c48', ['red', 'green', 'blue'])",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the select element"},
                "options": {
                    "oneOf": [
                        {"type": "string", "description": "Single option value or label to select"},
                        {"type": "array", "items": {"type": "string"}, "description": "Multiple option values or labels to select"}
                    ]
                }
            },
            "required": ["bid", "options"]
        }
    },
    {
        "name": "click",
        "description": "Click an element. Examples: click('a51'), click('b22', button='right'), click('48', button='middle', modifiers=['Shift'])",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the element to click"},
                "button": {"type": "string", "enum": ["left", "middle", "right"], "default": "left", "description": "Which mouse button to click"},
                "modifiers": {"type": "array", "items": {"type": "string", "enum": ["Alt", "Control", "Meta", "Shift"]}, "default": [], "description": "Keyboard modifiers to hold while clicking"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "dblclick",
        "description": "Double click an element. Examples: dblclick('12'), dblclick('ca42', button='right'), dblclick('178', button='middle', modifiers=['Shift'])",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the element to double-click"},
                "button": {"type": "string", "enum": ["left", "middle", "right"], "default": "left", "description": "Which mouse button to double-click"},
                "modifiers": {"type": "array", "items": {"type": "string", "enum": ["Alt", "Control", "Meta", "Shift"]}, "default": [], "description": "Keyboard modifiers to hold while double-clicking"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "hover",
        "description": "Hover over an element. Example: hover('b8')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the element to hover over"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "press",
        "description": "Focus the matching element and press a combination of keys. Accepts logical key names (Backspace, Tab, Enter, etc.) or single characters. Examples: press('88', 'Backspace'), press('a26', 'Control+a'), press('a61', 'Meta+Shift+t')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the element to focus"},
                "key_comb": {"type": "string", "description": "Key combination to press (e.g., 'Enter', 'Control+a', 'Meta+Shift+t')"}
            },
            "required": ["bid", "key_comb"]
        }
    },
    {
        "name": "focus",
        "description": "Focus the matching element. Example: focus('b455')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the element to focus"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "clear",
        "description": "Clear the input field. Example: clear('996')",
        "input_schema": {
            "type": "object",
            "properties": {
                "bid": {"type": "string", "description": "The browser ID of the input field to clear"}
            },
            "required": ["bid"]
        }
    },
    {
        "name": "drag_and_drop",
        "description": "Perform a drag & drop. Hover the element that will be dragged, press left mouse button, move to target element, release button. Example: drag_and_drop('56', '498')",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_bid": {"type": "string", "description": "The browser ID of the element to drag from"},
                "to_bid": {"type": "string", "description": "The browser ID of the element to drop onto"}
            },
            "required": ["from_bid", "to_bid"]
        }
    },
    {
        "name": "scroll",
        "description": "Scroll horizontally and vertically. Amounts in pixels, positive for right/down, negative for left/up. Examples: scroll(0, 200), scroll(-50.2, -100.5)",
        "input_schema": {
            "type": "object",
            "properties": {
                "delta_x": {"type": "number", "description": "Horizontal scroll amount in pixels (positive = right, negative = left)"},
                "delta_y": {"type": "number", "description": "Vertical scroll amount in pixels (positive = down, negative = up)"}
            },
            "required": ["delta_x", "delta_y"]
        }
    },
    {
        "name": "mouse_move",
        "description": "Move the mouse to a location. Uses absolute client coordinates in pixels. Example: mouse_move(65.2, 158.5)",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X coordinate in pixels"},
                "y": {"type": "number", "description": "Y coordinate in pixels"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_up",
        "description": "Move the mouse to a location then release a mouse button. Examples: mouse_up(250, 120), mouse_up(47, 252, 'right')",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X coordinate in pixels"},
                "y": {"type": "number", "description": "Y coordinate in pixels"},
                "button": {"type": "string", "enum": ["left", "middle", "right"], "default": "left", "description": "Which mouse button to release"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_down",
        "description": "Move the mouse to a location then press and hold a mouse button. Examples: mouse_down(140.2, 580.1), mouse_down(458, 254.5, 'middle')",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X coordinate in pixels"},
                "y": {"type": "number", "description": "Y coordinate in pixels"},
                "button": {"type": "string", "enum": ["left", "middle", "right"], "default": "left", "description": "Which mouse button to press"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_click",
        "description": "Move the mouse to a location and click a mouse button. Examples: mouse_click(887.2, 68), mouse_click(56, 712.56, 'right')",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X coordinate in pixels"},
                "y": {"type": "number", "description": "Y coordinate in pixels"},
                "button": {"type": "string", "enum": ["left", "middle", "right"], "default": "left", "description": "Which mouse button to click"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_dblclick",
        "description": "Move the mouse to a location and double click a mouse button. Examples: mouse_dblclick(5, 236), mouse_dblclick(87.5, 354, 'right')",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "number", "description": "X coordinate in pixels"},
                "y": {"type": "number", "description": "Y coordinate in pixels"},
                "button": {"type": "string", "enum": ["left", "middle", "right"], "default": "left", "description": "Which mouse button to double-click"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_drag_and_drop",
        "description": "Drag and drop from a location to a location. Uses absolute client coordinates in pixels. Example: mouse_drag_and_drop(10.7, 325, 235.6, 24.54)",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_x": {"type": "number", "description": "Starting X coordinate in pixels"},
                "from_y": {"type": "number", "description": "Starting Y coordinate in pixels"},
                "to_x": {"type": "number", "description": "Ending X coordinate in pixels"},
                "to_y": {"type": "number", "description": "Ending Y coordinate in pixels"}
            },
            "required": ["from_x", "from_y", "to_x", "to_y"]
        }
    },
    {
        "name": "keyboard_press",
        "description": "Press a combination of keys. Accepts logical key names or single characters. Examples: keyboard_press('Backspace'), keyboard_press('Control+a'), keyboard_press('Meta+Shift+t'), keyboard_press('PageDown')",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key or key combination to press (e.g., 'Enter', 'Control+a', '#')"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "keyboard_up",
        "description": "Release a keyboard key. Accepts logical key names or single characters. Examples: keyboard_up('Shift'), keyboard_up('c')",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to release (e.g., 'Shift', 'Control', 'a')"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "keyboard_down",
        "description": "Press and hold a keyboard key. Accepts logical key names or single characters. Examples: keyboard_down('Shift'), keyboard_down('c')",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to press and hold (e.g., 'Shift', 'Control', 'a')"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "keyboard_type",
        "description": "Types a string of text through the keyboard. Sends keydown, keypress/input, and keyup events for each character. Example: keyboard_type('Hello world!')",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type character by character"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "keyboard_insert_text",
        "description": "Insert a string of text in the currently focused element. Only dispatches input event, no keydown/keyup/keypress. Example: keyboard_insert_text('Hello world!')",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to insert directly into the focused element"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "goto",
        "description": "Navigate to a url. Example: goto('http://www.example.com')",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to"}
            },
            "required": ["url"]
        }
    }
]
