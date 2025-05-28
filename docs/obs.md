## Core Observation Structure

The observation is a dictionary with the following keys:

### Chat and Goal Information
- **`chat_messages`**: List of chat message dictionaries, each containing:
  - `role`: String ("user", "assistant", "infeasible", "info", "user_image")
  - `message`: String content of the message
  - `timestamp`: UTC timestamp when message was sent

- **`goal`**: String (legacy format) - text-only goal description
- **`goal_object`**: List (new format) - OpenAI-style message list with support for text and images:
  ```python
  [
    {"type": "text", "text": "Click the submit button"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
  ]
  ```

### Page State Information
- **`open_pages_urls`**: List of strings - URLs of all open browser tabs/pages
- **`active_page_index`**: NumPy array with single integer - index of currently active page
- **`url`**: String - URL of the currently active page

### Visual Information
- **`screenshot`**: 3D NumPy array (height, width, RGB) - screenshot of current page
  - Shape: `(-1, -1, 3)` (variable dimensions)
  - Data type: `uint8` (values 0-255)
  - Color channels: RGB format

### DOM Structure
- **`dom_object`**: Dictionary - Complete DOM snapshot from Chrome DevTools Protocol
  - Contains the full DOM tree including iframes
  - Includes layout information (bounding boxes, client rects, etc.)
  - Elements marked with `bid` attributes for interaction
  - Raw format from Chrome's DOMSnapshot.captureSnapshot

### Accessibility Tree
- **`axtree_object`**: Dictionary - Merged accessibility tree from Chrome DevTools
  - Flattened accessibility tree from all frames
  - Includes role, name, value, and properties for each accessible element
  - Elements marked with `browsergym_id` for interaction

### Element Properties
- **`extra_element_properties`**: Dictionary mapping bid → properties
  ```python
  {
    "a123": {
      "visibility": 0.85,  # Float 0-1, visibility ratio
      "bbox": [x, y, width, height],  # Bounding box coordinates
      "clickable": True,  # Boolean, whether element is clickable
      "set_of_marks": False  # Boolean, whether element is in set-of-marks
    }
  }
  ```

### Focus Information
- **`focused_element_bid`**: String - bid of currently focused element (empty if none)

### Action History
- **`last_action`**: String - the last action that was executed
- **`last_action_error`**: String - error message from last action (empty if no error)

### Timing
- **`elapsed_time`**: NumPy array with single float - seconds elapsed since episode start

### Browser Access
- **`browser`**: Direct reference to the Playwright browser object (for advanced use)

## Preprocessed Observations

The default `obs_preprocessor` adds additional text-based representations:

### Text Representations (added by preprocessor)
- **`dom_txt`**: String - flattened DOM as HTML text
- **`axtree_txt`**: String - flattened accessibility tree as indented text
- **`pruned_html`**: String - cleaned/simplified HTML representation

Example of `axtree_txt` format:
```
[a12] button "Submit"
  [a13] StaticText "Submit"
[a14] textbox "Email" value="user@example.com"
[a15] link "Home"
```

Example of `pruned_html` format:
```html
<button bid="a12">Submit</button>
<input bid="a14" type="email" value="user@example.com">
<a bid="a15" href="/">Home</a>
```

## Element Identification System

### BID (Browser ID) System
- Each interactive element gets a unique `bid` attribute (e.g., "a12", "b345")
- BIDs follow a hierarchical pattern for nested frames:
  - "a" - element in main frame
  - "aB" - frame element in main frame
  - "aB12" - element in frame "aB"
  - "aBc34" - element in nested frame "aBc"

### Visibility and Interaction Properties
- **Visibility**: Float 0-1 indicating how much of element is visible
- **Clickable**: Boolean indicating if element responds to clicks
- **Set of Marks**: Boolean indicating if element is marked for attention

## Space Definitions

The observation space is formally defined as:
```python
gym.spaces.Dict({
    "chat_messages": gym.spaces.Sequence(...),
    "goal": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
    "goal_object": gym.spaces.Sequence(AnyDict()),
    "open_pages_urls": gym.spaces.Sequence(Unicode(...)),
    "active_page_index": gym.spaces.Box(low=0, high=255, dtype=int),
    "url": Unicode(...),
    "screenshot": AnyBox(low=0, high=255, shape=(-1, -1, 3), dtype=np.uint8),
    "dom_object": AnyDict(),
    "axtree_object": AnyDict(),
    "extra_element_properties": AnyDict(),
    "focused_element_bid": Unicode(...),
    "last_action": Unicode(...),
    "last_action_error": Unicode(...),
    "elapsed_time": gym.spaces.Box(low=0, high=np.inf, dtype=float),
    "browser": AnyDict(),
})
```
