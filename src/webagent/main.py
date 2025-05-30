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
from webagent.utils import message_to_action_str, print_context, print_usage, save_history_to_txt, flatten_conversation_history, image_to_base64_url, purge_old_tags

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
- if you have already submitted (i.e. sent an email, or bought something), do not attempt to submit again

Finally, and perhaps the most importantly, if you need to remember something, write it into your response (either thinking or user response).
This is important because page state is removed over time to save context space, so if you need to remember URLs for example, write them down and you can use them in a goto() later.

There is always a "correct" path to take. Sometimes it's not obvious, for example, filling in a form in a search result instead of clicking into the result and filling it out there.
"""

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
    
    if not diff_text:
        return "No changes in page state."
    
    return f"Page state changes:\n{diff_text}"


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
            demo_mode="off",
            # demo_mode="default",
        )
        
        self.client = anthropic.Anthropic()
        self.conversation_history: list[MessageParam] = []
        self.previous_axtree: str | None = None
        self.iteration_count = 0

    def query_model(self, obs: Any) -> tuple[str, ContentBlock | None, MessageParam]:
        self.iteration_count += 1
    
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
        
        # Pass the current reset flag to purge_old_tags
        self.conversation_history = purge_old_tags(self.conversation_history, iterations_to_keep=5, current_has_reset=is_full_reset)
    
        important_section = ""
        if self.iteration_count % 3 == 1:
            important_section = """\
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
</important>"""
    
        # Create current message
        current_message = f"""\
<goal>{obs['goal']}</goal>
{state_tag}
{important_section}
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
            system=[{
                "type": "text",
                "text": INSTRUCTIONS,
                "cache_control": {"type": "ephemeral"}
            }],
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
        headless=False,
        max_steps=120,
        leaderboard=True,
        run_id="KISS-1",
        # results_dir="demo_results",
        cache_only=True
    )
    # harness.env_args["record_video"] = True

    results = harness.run()
