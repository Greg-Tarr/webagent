def refresh():
    """
    Refresh/reload the current page with comprehensive cache clearing.

    Examples:
        refresh()
    """
    import time
    
    try:
        page.context.clear_cookies()
        print("Successfully cleared cookies")
    except Exception as e:
        print(f"Failed to clear cookies: {e}")

    try:
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        print("Successfully cleared localStorage and sessionStorage")
    except Exception as e:
        print(f"Failed to clear localStorage/sessionStorage: {e}")

    try:
        page.evaluate("() => { if ('caches' in window) { caches.keys().then(names => names.forEach(name => caches.delete(name))); } }")
        print("Successfully cleared caches")
    except Exception as e:
        print(f"Failed to clear caches: {e}")
    
    page.reload(wait_until="networkidle", timeout=30000)
    time.sleep(3)

def take_screenshot():
    """
    Take a screenshot of the current page and return the image data.
    
    Examples:
        take_screenshot()
    """
    return "screenshot_requested"
