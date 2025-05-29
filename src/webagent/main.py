import os
import time
os.environ['TZ'] = 'America/New_York'
time.tzset()

import base64
import io
import difflib
import dataclasses
from typing import Any
from datetime import datetime
import uuid

import numpy as np
from PIL import Image
from agisdk import REAL
from agisdk.REAL import AbstractAgentArgs, Agent
from agisdk.REAL.browsergym import HighLevelActionSet
from agisdk.REAL.browsergym.experiments import AgentInfo
from anthropic.types import ContentBlock, Message, MessageParam
from dotenv import load_dotenv
import anthropic

from webagent.custom_actions import refresh, take_screenshot
from webagent.tools import TOOLS

load_dotenv()

INSTRUCTIONS = """\
Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
When you are finished, return to the user (via the send_msg_to_user function) the result of your actions.
It is critical you think about each step in the section below in EVERY thinking process. Be verbose, timid, self-doubting and exceptionally careful.

User Details (for any forms that say "you can put in anything you'd like", otherwise use the details stated in 'goal')
- Name: Greg Tarr
- Age: 22
- Email: gregoryguytarr@gmail.com
- Phone: +1-418-543-8090
- Address: 777 Brockton Avenue, Abington MA 2351
- SSN: 123-45-6789

If you notice you have made a mistake, use navigation to reset (e.g. go_back). Alternatively, if something
is not working as expected, you can try:
- focusing something before clicking/filling
- clicking instead of filling (and vice versa)
- refreshing the page (it usually takes 2 refreshes)
- going back to a previous page and retrying

Remember:
- double check your work before proceeding,
- think "is there anything wrong with the current state?" if the answer is yes, revert using go_back and try a different approach
- do not proceed if you have made a mistake.
- if you have made a mistake, revert using go_back and try a different approach
- there are no display issues, rely on the screen and not information in the url (the url may be incorrect).
- be liberal with your reversions, you have one chance, so navigating backwards is fine.
- the final result has to be exactly correct, exactly! if it's even slightly wrong you should start over
- a different approach could be as simple as navigating to a page instead of clicking an easily accessible button!
- for example, if you can see what you're looking for, why not click it instead of searching for it?
- if skeletons are showing, or something is missing or showing, reload the page!
- do not use send_msg_to_user until the very end.
- for date pickers or dropdowns, use 'click' instead of 'fill'
- don't do things more than twice, try different approaches, think "is there any other way to achieve the same result?"
- feel free to explore
- feel free to make liberal use of goto() in order to clear url params if they are hindering your progress
- some tasks are searches through many items, in that case, before analyzing a specific item, click next buttons or pagination options to count the total number of unique items. you MUST do this first AND last.
- your first actions should be exploratory, e.g. clicking 'next slide' or 'next page' until you've itemized everything in memory.
- do not assume that the number of items on the page is the total catalogue
- if you are stuck on a specific element, e.g. a button appears as static text rather than clickable, it may be worth taking a screenshot and then using coordinates, but use it sparingly

Finally, and perhaps the most importantly, if you need to remember something, write it into your response (either thinking or user response).
This is important because page state is removed over time to save context space, so if you need to remember URLs for example, write them down and you can use them in a goto() later.

There is always a "correct" path to take. Sometimes it's not obvious, for example, filling in a form in a search result instead of clicking into the result and filling it out there.
"""

def message_to_action_str(message: Message) -> str:
    # Find the tool_use block in the message content
    tool_use_block = None
    for block in message.content:
        if block.type == "tool_use":
            tool_use_block = block
            break
    
    if tool_use_block:
        args_list = []
        for k, v in tool_use_block.input.items(): # pyright: ignore
            if isinstance(v, (int, float)):
                args_list.append(f'{k}={v}')
            elif isinstance(v, bool):
                args_list.append(f'{k}={str(v).lower()}')
            elif v is None:
                args_list.append(f'{k}=None')
            else:
                value_str = str(v)
                value_str = value_str.replace('\n', '\\n').replace('\r', '\\r').replace('"', '\\"')
                args_list.append(f'{k}="{value_str}"')
        
        args_str = ", ".join(args_list)
        return f"{tool_use_block.name}({args_str})"
    
    # If no tool use, check if there's text content that might indicate completion
    for block in message.content:
        if block.type == "text" and block.text:
            if any(phrase in block.text.lower() for phrase in ["complete", "done", "finished", "goal accomplished"]):
                return "send_msg_to_user(text=\"Task completed successfully.\")"
    
    # Default fallback - use a valid noop action
    return "send_msg_to_user(text=\"No action needed.\")"

def print_context(tools, messages):
    # print("Available tools:")
    # for tool in tools:
    #     print(f"  - {tool['name']}: {tool.get('description', 'No description')}")

    print("\n\n\nMessages:")
    for i, message in enumerate(messages):
        print(f"  Message {i+1} ({message['role']}):")
        
        content = message.get('content', [])
        if isinstance(content, str):
            print(f"    Text: {content}")
        elif isinstance(content, list):
            for j, block in enumerate(content):
                # Handle anthropic ContentBlock objects
                if hasattr(block, 'type'):
                    if block.type == 'text':
                        text = getattr(block, 'text', '')
                        print(f"    Text {j+1}: {text}")
                    elif block.type == 'tool_use':
                        name = getattr(block, 'name', '')
                        input_args = getattr(block, 'input', {})
                        print(f"    Tool Use {j+1}: {name}({input_args})")
                    elif block.type == 'tool_result':
                        tool_use_id = getattr(block, 'tool_use_id', '')
                        result_content = getattr(block, 'content', '')
                        print(f"    Tool Result {j+1}: ID={tool_use_id}, Content={result_content}")
                    elif block.type == 'thinking':
                        thinking_text = getattr(block, 'thinking', '')
                        truncated_thinking = thinking_text[:400] + "..." if len(thinking_text) > 400 else thinking_text
                        print(f"    Thinking {j+1}: {truncated_thinking}")
                    else:
                        print(f"    Block {j+1} ({block.type}): {str(block)[:100]}...")
                
                # Handle dictionary representations
                elif isinstance(block, dict):
                    block_type = block.get('type', 'unknown')
                    if block_type == 'text':
                        text = block.get('text', '')
                        print(f"    Text {j+1}: {text}")
                    elif block_type == 'tool_use':
                        name = block.get('name', '')
                        input_args = block.get('input', {})
                        print(f"    Tool Use {j+1}: {name}({input_args})")
                    elif block_type == 'tool_result':
                        tool_use_id = block.get('tool_use_id', '')
                        result_content = block.get('content', '')
                        print(f"    Tool Result {j+1}: ID={tool_use_id}, Content={result_content}")
                    elif block_type == 'thinking':
                        thinking_text = block.get('thinking', '')
                        # Truncate thinking text if it's very long
                        truncated_thinking = thinking_text[:400] + "..." if len(thinking_text) > 400 else thinking_text
                        print(f"    Thinking {j+1}: {truncated_thinking}")
                    else:
                        print(f"    Block {j+1} ({block_type}): {str(block)[:100]}...")
                else:
                    print(f"    Block {j+1}: {str(block)[:100]}...")
        else:
            print(f"    Content: {str(content)[:100]}...")
        print()

def print_usage(usage):
    print(f"Usage - Input tokens: {usage.input_tokens}, Output tokens: {usage.output_tokens}")
    if usage.cache_creation_input_tokens:
        print(f"Cache creation input tokens: {usage.cache_creation_input_tokens}")
    if usage.cache_read_input_tokens:
        print(f"Cache read input tokens: {usage.cache_read_input_tokens}")

def save_history_to_txt(agent_id: str, conversation_history: list[MessageParam], filename: str = "conversation_history.txt"):
    """Save conversation history to a text file in a folder structure based on agent_id."""
    # Create folder structure: logs/agent_id/filename
    log_dir = os.path.join("logs", agent_id)
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        timestamped_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
    else:
        timestamped_filename = f"{filename}_{timestamp}"

    full_path = os.path.join(log_dir, timestamped_filename)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(f"=== Conversation History - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

        for i, message in enumerate(conversation_history):
            f.write(f"=== Message {i+1} ===\n")
            f.write(f"Role: {message['role']}\n")

            if isinstance(message['content'], list):
                for j, content_block in enumerate(message['content']):
                    if hasattr(content_block, 'type'):
                        if content_block.type == 'text':
                            f.write(f"Text Content {j+1}:\n{getattr(content_block, 'text', '')}\n")
                        elif content_block.type == 'tool_use':
                            f.write(f"Tool Use {j+1}:\n")
                            f.write(f"  Name: {getattr(content_block, 'name', '')}\n")
                            f.write(f"  Input: {getattr(content_block, 'input', {})}\n")
                            f.write(f"  ID: {getattr(content_block, 'id', '')}\n")
                        elif content_block.type == 'thinking':
                            thinking_text = getattr(content_block, 'thinking', '')
                            f.write(f"Thinking {j+1}:\n{thinking_text}\n")
                        else:
                            f.write(f"Content Block {j+1} ({content_block.type}): {content_block}\n")
                    elif isinstance(content_block, dict):
                        if content_block.get('type') == 'text':
                            f.write(f"Text Content {j+1}:\n{content_block.get('text', '')}\n")
                        elif content_block.get('type') == 'tool_use':
                            f.write(f"Tool Use {j+1}:\n")
                            f.write(f"  Name: {content_block.get('name', '')}\n")
                            f.write(f"  Input: {content_block.get('input', {})}\n")
                            f.write(f"  ID: {content_block.get('id', '')}\n")
                        elif content_block.get('type') == 'tool_result':
                            f.write(f"Tool Result {j+1}:\n")
                            f.write(f"  Tool Use ID: {content_block.get('tool_use_id', '')}\n")
                            f.write(f"  Content: {content_block.get('content', '')}\n")
                        elif content_block.get('type') == 'thinking':
                            thinking_text = content_block.get('thinking', '')
                            f.write(f"Thinking {j+1}:\n{thinking_text}\n")
                        else:
                            f.write(f"Content Block {j+1}: {content_block}\n")
                    else:
                        f.write(f"Content Block {j+1}: {content_block}\n")
            else:
                f.write(f"Content: {message['content']}\n")

            f.write("\n")

def flatten_conversation_history(conversation_history: list[MessageParam]) -> list[MessageParam]:
    """Flatten nested conversation history to make it compatible with agisdk."""
    flattened = []

    for message in conversation_history:
        if isinstance(message.get('content'), list):
            # Convert content blocks to simple text representation
            text_parts = []
            for block in message['content']:
                if hasattr(block, 'type'):
                    if block.type == 'text': # pyright: ignore
                        text_parts.append(getattr(block, 'text', ''))
                    elif block.type == 'tool_use': # pyright: ignore
                        tool_name = getattr(block, 'name', '')
                        tool_input = getattr(block, 'input', {})
                        text_parts.append(f"Tool: {tool_name}({tool_input})")
                    elif block.type == 'tool_result': # pyright: ignore
                        result_content = getattr(block, 'content', '')
                        text_parts.append(f"Result: {result_content}")
                elif isinstance(block, dict):
                    if block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                    elif block.get('type') == 'tool_use':
                        tool_name = block.get('name', '')
                        tool_input = block.get('input', {})
                        text_parts.append(f"Tool: {tool_name}({tool_input})")
                    elif block.get('type') == 'tool_result':
                        result_content = block.get('content', '')
                        text_parts.append(f"Result: {result_content}")

            flattened_message: MessageParam = {
                "role": message["role"],
                "content": "\n".join(text_parts)
            }
            flattened.append(flattened_message)
        else:
            # Already flat, just add as is
            flattened.append(message)

    return flattened

def image_to_base64_url(image: np.ndarray) -> str:
    """Convert a numpy array to a base64 encoded image url."""
    
    if isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    else:
        pil_image = image
        
    if pil_image.mode in ("RGBA", "LA"):
        pil_image = pil_image.convert("RGB")

    with io.BytesIO() as buffer:
        pil_image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/jpeg;base64,{image_base64}"

def generate_axtree_diff(previous_axtree: str | None, current_axtree: str, change_threshold: float = 0.7) -> str:
    """
    Generate a git-style diff between two axtree states.
    If changes exceed threshold, return full new state instead.
    
    Args:
        previous_axtree: Previous DOM state
        current_axtree: Current DOM state  
        change_threshold: If ratio of changed lines > this, show full state (default 0.7 = 70%)
    """
    if previous_axtree is None:
        return f"Initial state:\n{current_axtree}"
    
    previous_lines = previous_axtree.splitlines(keepends=True)
    current_lines = current_axtree.splitlines(keepends=True)
    
    # Calculate similarity ratio
    similarity = difflib.SequenceMatcher(None, previous_lines, current_lines).ratio()
    
    # If similarity is too low (major page change), return full new state
    if similarity < (1 - change_threshold):
        return f"Major page change detected (similarity: {similarity:.2f})\nNew page state:\n{current_axtree}"
    
    diff = difflib.unified_diff(
        previous_lines,
        current_lines,
        fromfile="previous_state",
        tofile="current_state",
        lineterm=""
    )
    
    diff_text = ''.join(diff)
    
    # If no changes, return a simple message
    if not diff_text:
        return "No changes in page state."
    
    return f"Page state changes:\n{diff_text}"

def purge_old_tags(conversation_history: list[MessageParam], iterations_to_keep: int = 5) -> list[MessageParam]:
    """
    Replace goal and important tags older than specified iterations with placeholder text.
    Remove old images to prevent memory bloat.
    Only replace state tags if we've had a full page reset (full_reset=True).
    """
    # Count assistant messages (iterations) from the end
    assistant_count = 0
    cutoff_index = len(conversation_history)
    
    for i in range(len(conversation_history) - 1, -1, -1):
        if conversation_history[i].get('role') == 'assistant':
            assistant_count += 1
            if assistant_count >= iterations_to_keep:
                cutoff_index = i
                break
    
    # Check if we have a full reset state tag in recent messages
    has_full_reset = False
    for i in range(cutoff_index, len(conversation_history)):
        message = conversation_history[i]
        if message.get('role') == 'user' and isinstance(message.get('content'), list):
            for block in message['content']:
                if hasattr(block, 'type') and block.type == 'text':
                    text = getattr(block, 'text', '')
                elif isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                else:
                    continue
                
                if '<state full_reset=True>' in text:
                    has_full_reset = True
                    break
            if has_full_reset:
                break
    
    # Process messages
    purged_history = []
    
    for i, message in enumerate(conversation_history):
        if message.get('role') == 'user' and isinstance(message.get('content'), list):
            new_content = []
            for block in message['content']:
                # Handle tool_result blocks specially
                if isinstance(block, dict) and block.get('type') == 'tool_result':
                    if i < cutoff_index:  # Old message
                        # Check if tool_result contains images
                        content = block.get('content', [])
                        if isinstance(content, list):
                            # Remove images from old tool results, keep text
                            filtered_content = []
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'image':
                                    # Skip old images
                                    continue
                                else:
                                    filtered_content.append(item)
                            
                            if filtered_content:  # Only keep if there's still content
                                new_block = block.copy()
                                new_block['content'] = filtered_content
                                new_content.append(new_block)
                        else:
                            # Non-list content, keep as is
                            new_content.append(block)
                    else:
                        # Recent message, keep all tool results including images
                        new_content.append(block)
                
                # Handle direct image blocks (if any exist at top level)
                elif (hasattr(block, 'type') and block.type == 'image') or \
                     (isinstance(block, dict) and block.get('type') == 'image'):
                    if i >= cutoff_index:  # Only keep recent images
                        new_content.append(block)
                    # Old images are dropped (not added to new_content)
                
                # Handle text blocks with tag replacement
                elif hasattr(block, 'type') and block.type == 'text':
                    text = getattr(block, 'text', '')
                    block_dict = {"type": "text", "text": text}
                    
                    # Only process messages older than the cutoff
                    if i < cutoff_index:
                        # Replace old goal tags with placeholder
                        if '<goal>' in text and '</goal>' in text:
                            import re
                            text = re.sub(r'<goal>.*?</goal>', '<goal>old info, removed</goal>', text, flags=re.DOTALL)
                            block_dict['text'] = text
                        
                        # Replace old important tags with placeholder
                        if '<important>' in text and '</important>' in text:
                            import re
                            text = re.sub(r'<important>.*?</important>', '<important>old info, removed</important>', text, flags=re.DOTALL)
                            block_dict['text'] = text
                        
                        # Replace old state tags only if we have a full reset
                        if has_full_reset and '<state' in text and '</state>' in text:
                            import re
                            text = re.sub(r'<state[^>]*>.*?</state>', '<state>old info, removed</state>', text, flags=re.DOTALL)
                            block_dict['text'] = text
                    
                    # Add the (possibly modified) text block
                    new_content.append(block_dict)
                
                elif isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                    block_dict = block.copy()
                    
                    # Only process messages older than the cutoff
                    if i < cutoff_index:
                        # Replace old goal tags with placeholder
                        if '<goal>' in text and '</goal>' in text:
                            import re
                            text = re.sub(r'<goal>.*?</goal>', '<goal>old info, removed</goal>', text, flags=re.DOTALL)
                            block_dict['text'] = text
                        
                        # Replace old important tags with placeholder
                        if '<important>' in text and '</important>' in text:
                            import re
                            text = re.sub(r'<important>.*?</important>', '<important>old info, removed</important>', text, flags=re.DOTALL)
                            block_dict['text'] = text
                        
                        # Replace old state tags only if we have a full reset
                        if has_full_reset and '<state' in text and '</state>' in text:
                            import re
                            text = re.sub(r'<state[^>]*>.*?</state>', '<state>old info, removed</state>', text, flags=re.DOTALL)
                            block_dict['text'] = text
                    
                    # Add the (possibly modified) text block
                    new_content.append(block_dict)
                
                else:
                    # Keep other block types as is (but we've handled the main ones above)
                    new_content.append(block)
            
            if new_content:  # Only add message if it has content left
                purged_message: MessageParam = {
                    "role": message["role"],
                    "content": new_content
                }
                purged_history.append(purged_message)
        else:
            # Keep assistant messages and other message types as is
            purged_history.append(message)
    
    return purged_history
    
class GTAgent(Agent):
    def __init__(self) -> None:
        super().__init__()

        self.agent_id = f"{int(datetime.now().timestamp() * 1000000):016d}_{uuid.uuid4().hex[:8]}"
        self.finished = False
        self.action_set = HighLevelActionSet(
            subsets=["chat", "bid", "infeas", "coord",  "tab", "nav", "custom"],
            custom_actions=[refresh, take_screenshot],
            strict=False,
            multiaction=False,
            demo_mode="off"
        )
        
        self.client = anthropic.Anthropic()
        self.conversation_history: list[MessageParam] = []
        self.previous_axtree: str | None = None

    def query_model(self, obs: Any) -> tuple[str, ContentBlock | None, MessageParam]:
        # Handle last tool's result
        if self.conversation_history:
            last_message = self.conversation_history[-1]
            if isinstance(last_message.get('content'), list):
                last_tool_use = next(
                    (block for block in last_message['content'] 
                     if (hasattr(block, 'type') and block.type == 'tool_use') or 
                        (isinstance(block, dict) and block.get('type') == 'tool_use')),
                    None
                )
                
                if last_tool_use:
                    tool_use_id = last_tool_use.id if hasattr(last_tool_use, 'id') else last_tool_use.get('id', '')
                    tool_name = last_tool_use.name if hasattr(last_tool_use, 'name') else last_tool_use.get('name', '')
                    
                    # Handle different tool results
                    if obs.get('last_action_error'):
                        result_content = f"Error: {obs['last_action_error']}"
                        tool_result: MessageParam = {
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result_content
                            }]
                        }
                    elif tool_name == "take_screenshot":
                        # For screenshots, include the current screenshot from obs
                        screenshot_base64 = image_to_base64_url(obs['screenshot'])
                        
                        tool_result: MessageParam = {
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Here is the current screenshot of the page:"
                                    },
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/jpeg",
                                            "data": screenshot_base64.split(",")[1]  # Remove data:image/jpeg;base64, prefix
                                        }
                                    }
                                ]
                            }]
                        }
                    else:
                        # Default success message for other tools
                        result_content = "Success"
                        tool_result: MessageParam = {
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result_content
                            }]
                        }
                    
                    self.conversation_history.append(tool_result)

        # Generate diff instead of full state
        axtree_info = generate_axtree_diff(self.previous_axtree, obs['axtree_txt'])
        is_full_reset = "Major page change detected" in axtree_info or "Initial state:" in axtree_info
        self.previous_axtree = obs['axtree_txt']
        state_tag = f"<state full_reset={is_full_reset}>{axtree_info}</state>"
        
        self.conversation_history = purge_old_tags(self.conversation_history, iterations_to_keep=5)
        
        # Create current message
        current_message = f"""\
<goal>{obs['goal']}</goal>
{state_tag}
<important>
Remember:
- double check your work before proceeding,
- think "is there anything wrong with the current state?" if the answer is yes, revert using go_back and try a different approach
- do not proceed if you have made a mistake.
- if you have made a mistake, revert using go_back and try a different approach
- there are no display issues, rely on the screen and not information in the url (the url may be incorrect).
- be liberal with your reversions, you have one chance, so navigating backwards is fine.
- the final result has to be exactly correct, exactly! if it's even slightly wrong you should start over
- a different approach could be as simple as navigating to a page instead of clicking an easily accessible button!
- for example, if you can see what you're looking for, why not click it instead of searching for it?
- if skeletons are showing, or something is missing or showing, reload the page!
- do not use send_msg_to_user until the very end.
- for date pickers or dropdowns, use 'click' instead of 'fill'
- don't do things more than twice, try different approaches, think "is there any other way to achieve the same result?"
- feel free to explore
- feel free to make liberal use of goto() in order to clear url params if they are hindering your progress
- some tasks are searches through many items, in that case, before analyzing a specific item, click next buttons or pagination options to count the total number of unique items. you MUST do this first AND last.
- your first actions should be exploratory, e.g. clicking 'next slide' or 'next page' until you've itemized everything in memory.
- do not assume that the number of items on the page is the total catalogue
- it's good practice to take a screenshot before submitting just in case there's a visual difference, even if the answer is clear ESPECIALLY when it comes to flights!

Finally, and perhaps the most importantly, if you need to remember something, write it into your response (either thinking or user response).
This is important because page state is removed over time to save context space, so if you need to remember URLs for example, write them down and you can use them in a goto() later.

</important>
"""
        user_message: MessageParam = {
            "role": "user",
            "content": [{"type": "text", "text": current_message}]
        }
        messages = self.conversation_history + [user_message]
        available_tools = [
            tool for tool in TOOLS 
            if tool["name"] in self.action_set.action_set.keys()  # pyright: ignore
        ]

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=20000,
            temperature=1,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000
            },
            system=INSTRUCTIONS,
            messages=messages,
            tool_choice={"type": "auto"},
            tools=available_tools # pyright: ignore
        )
        print_usage(response.usage)
        action = message_to_action_str(response)
        
        response_blocks: MessageParam = {
            "role": "assistant",
            "content": response.content
        }
        messages.append(response_blocks)

        print_context(available_tools, messages)
        save_history_to_txt(self.agent_id, messages)
        
        self.conversation_history = messages

        thinking_block = next(filter(lambda block: block.type == "thinking", response.content), None)

        return action, thinking_block, response_blocks
        
    def obs_preprocessor(self, obs: dict) -> Any:
        return super().obs_preprocessor(obs)

    def get_action(self, obs: Any) -> tuple[str | None, AgentInfo]: # pyright: ignore
        if self.finished:
            return None, AgentInfo(
                think="",
                chat_messages=flatten_conversation_history(self.conversation_history)
            )

        action, thinking_block, response_blocks = self.query_model(obs)
        print(f"Action: {action}")
        
        self.finished = "send_msg_to_user" in action or any(phrase in action.lower() for phrase in ["complete", "done", "finished", "goal accomplished"])
        print(f"Finished: {self.finished}")
        
        return action, AgentInfo(
            think=thinking_block.thinking if thinking_block else "", # pyright: ignore
            chat_messages=flatten_conversation_history(self.conversation_history)
        ) 
        



@dataclasses.dataclass
class GTAgentArgs(AbstractAgentArgs):
    agent_name: str = "DemoAgent"
    
    def make_agent(self):
        return GTAgent()


if __name__ == "__main__":
    agent_args = GTAgentArgs()
    
    harness = REAL.harness(
        agentargs=agent_args,
        task_name="webclones.fly-unified-13",
        headless=False,
        max_steps=999,
        leaderboard=False,
        run_id="None",
    )

    results = harness.run()
