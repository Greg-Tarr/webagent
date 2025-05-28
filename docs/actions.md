
## High-Level Actions (default action set):

### Communication Actions:
- `send_msg_to_user(text)` - Send a message to the user
- `report_infeasible(reason)` - Report that instructions are infeasible

### Basic Actions:
- `noop()` - Do nothing
- `noop(wait_ms)` - Do nothing and wait for specified milliseconds

### Element Interaction Actions (using bid):
- `fill(bid, value)` - Fill out a form field
- `click(bid)` - Click an element
- `click(bid, button)` - Click with specific mouse button ("left", "middle", "right")
- `click(bid, button, modifiers)` - Click with button and modifiers (["Alt", "Control", "Meta", "Shift"])
- `dblclick(bid)` - Double click an element
- `dblclick(bid, button)` - Double click with specific button
- `dblclick(bid, button, modifiers)` - Double click with button and modifiers
- `hover(bid)` - Hover over an element
- `press(bid, key_comb)` - Press key combination on element
- `focus(bid)` - Focus an element
- `clear(bid)` - Clear an input field
- `drag_and_drop(from_bid, to_bid)` - Drag from one element to another
- `upload_file(bid, file)` - Upload file(s) to an element
- `select_option(bid, options)` - Select option(s) in a select element

### Scrolling:
- `scroll(delta_x, delta_y)` - Scroll by pixel amounts

### Navigation Actions:
- `goto(url)` - Navigate to a URL
- `go_back()` - Navigate back in history
- `go_forward()` - Navigate forward in history

### Tab Actions:
- `new_tab()` - Open a new tab
- `tab_close()` - Close current tab
- `tab_focus(index)` - Focus a specific tab by index

## Coordinate-Based Actions (if enabled with "coord" subset):

### Mouse Actions:
- `mouse_move(x, y)` - Move mouse to coordinates
- `mouse_click(x, y)` - Click at coordinates
- `mouse_click(x, y, button)` - Click with specific button
- `mouse_dblclick(x, y)` - Double click at coordinates
- `mouse_dblclick(x, y, button)` - Double click with specific button
- `mouse_up(x, y)` - Release mouse button at coordinates
- `mouse_up(x, y, button)` - Release specific button
- `mouse_down(x, y)` - Press mouse button at coordinates
- `mouse_down(x, y, button)` - Press specific button
- `mouse_drag_and_drop(from_x, from_y, to_x, to_y)` - Drag from one position to another
- `mouse_upload_file(x, y, file)` - Click location and upload file(s)

### Keyboard Actions:
- `keyboard_press(key)` - Press a key combination
- `keyboard_up(key)` - Release a key
- `keyboard_down(key)` - Hold down a key
- `keyboard_type(text)` - Type text character by character
- `keyboard_insert_text(text)` - Insert text directly

## Notes:

1. **bid** = browsergym element ID (e.g., "a123", "b45")
2. **button** = "left", "middle", or "right"
3. **modifiers** = list containing any of ["Alt", "Control", "Meta", "Shift"]
4. **key_comb** = keyboard keys/combinations (e.g., "Enter", "Control+a", "Meta+Shift+t")
5. **file** = file path string or list of file paths
6. **options** = string or list of strings for select options
7. **x, y** = numeric coordinates in pixels
8. **delta_x, delta_y** = scroll amounts in pixels (positive for right/down)
9. **index** = numeric tab index
