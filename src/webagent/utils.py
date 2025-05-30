import os
import base64
import io
from datetime import datetime

import numpy as np
from PIL import Image
from anthropic.types import Message

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

def save_history_to_txt(agent_id: str, conversation_history: list[dict], filename: str = "conversation_history.txt"):
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

def flatten_conversation_history(conversation_history: list[dict]) -> list[dict]:
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

            flattened_message = {
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

def purge_old_tags(conversation_history: list[dict], iterations_to_keep: int = 5, current_has_reset: bool = False) -> list[dict]:
    """
    Replace goal and important tags older than specified iterations with placeholder text.
    Remove old images to prevent memory bloat.
    Only replace state tags if we've had a full page reset (full_reset=True) or current_has_reset=True.
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
    
    # Check if we have a full reset state tag in recent messages OR current iteration has reset
    has_full_reset = current_has_reset
    if not has_full_reset:
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
                purged_message = {
                    "role": message["role"],
                    "content": new_content
                }
                purged_history.append(purged_message)
        else:
            # Keep assistant messages and other message types as is
            purged_history.append(message)
    
    return purged_history
