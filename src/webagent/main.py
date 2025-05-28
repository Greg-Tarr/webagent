import os
import dataclasses
from typing import Any
from datetime import datetime

from agisdk import REAL
from agisdk.REAL import AbstractAgentArgs, Agent
from agisdk.REAL.browsergym import HighLevelActionSet
from agisdk.REAL.browsergym.experiments import AgentInfo
from anthropic.types import ContentBlock, Message, MessageParam
from dotenv import load_dotenv
import anthropic

from webagent.tools import TOOLS

load_dotenv()

INSTRUCTIONS = """\
Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.
When you are finished, return to the user (via the send_msg_to_user function) the result of your actions.
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
            # Handle numeric values properly - don't quote them
            if isinstance(v, (int, float)):
                args_list.append(f'{k}={v}')
            elif isinstance(v, bool):
                args_list.append(f'{k}={str(v).lower()}')
            elif v is None:
                args_list.append(f'{k}=None')
            else:
                # For string values, handle newlines and quotes properly
                value_str = str(v)
                # Replace newlines with \n and escape quotes
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
    print("Available tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")

    print("\nMessages:")
    for i, message in enumerate(messages):
        print(f"  Message {i+1}:")
        print(f"    {message}")

def save_history_to_txt(conversation_history: list[MessageParam], filename: str = "logs/conversation_history.txt"):
    """Save conversation history to a text file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        timestamped_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
    else:
        timestamped_filename = f"{filename}_{timestamp}"

    with open(timestamped_filename, 'w', encoding='utf-8') as f:
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


class GTAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        
        self.finished = False
        self.action_set = HighLevelActionSet(
            subsets=["chat", "bid", "infeas", "tab"],
            strict=False,
            multiaction=False,
            demo_mode="off"
        )
        
        self.client = anthropic.Anthropic()
        self.conversation_history: list[MessageParam] = []


    def query_model(self, obs: Any) -> tuple[str, ContentBlock | None, MessageParam]:
        current_message = f"Goal: {obs['goal']}\nCurrent state: {obs['axtree_txt']}" # TODO: make this a diff
        user_message: MessageParam = {
            "role": "user",
            "content": [{"type": "text", "text": current_message}]
        }
        messages = self.conversation_history + [user_message]
        available_tools = [
            tool for tool in TOOLS 
            if tool["name"] in self.action_set.action_set.keys()  # pyright: ignore
        ]
        print_context(available_tools, messages)
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
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

        action = message_to_action_str(response)
        
        response_blocks: MessageParam = {
            "role": "assistant",
            "content": response.content
        }
        messages.append(response_blocks)

        tool_use_block = next(filter(lambda block: block.type == "tool_use", response.content), None)
        if tool_use_block: # Append a result saying it succeeded (TODO: make this a diff from the previous state)
            messages.append(
                {"role": "user", "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id, # pyright: ignore
                    "content": "success"
                }]}
            )

        save_history_to_txt(messages)
        
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
        
        self.finished = "noop" in action.lower() or "send_msg_to_user" in action or any(phrase in action.lower() for phrase in ["complete", "done", "finished", "goal accomplished"])
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
        task_name="webclones.omnizon-10",
        headless=False,
        max_steps=25,
        leaderboard=False,
        run_id="None",
    )

    results = harness.run()
