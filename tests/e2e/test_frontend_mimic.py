import pytest
import os
from playwright.sync_api import Page, expect

def test_interactive_terminal_execution(page: Page):
    """
    Automated E2E Test (Frontend Mimic)
    This test validates the interactive_terminal.html by simulating a real user.
    It verifies that the WebSockets work, code compiles, and outputs stream back.
    """
    
    # 1. Open the local HTML file (Frontend Mimic)
    # Using absolute path for local file testing
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    html_path = os.path.join(current_dir, "interactive_terminal.html")
    page.goto(f"file://{html_path}")

    # 2. Validate initial state
    expect(page.locator("#connectionStatus")).to_have_text("Disconnected")
    expect(page.locator("#exeBtn")).to_have_text("Execute")
    
    # Select C++ engine
    page.locator("#langSelect").select_option("cpp")

    # 3. Simulate User Clicking Execute
    page.locator("#exeBtn").click()

    # 4. Wait for WebSocket connection to open and UI to update
    expect(page.locator("#connectionStatus")).to_have_text("Connected", timeout=5000)
    
    # Wait for the system to say it submitted code
    terminal_output = page.locator("#terminal")
    expect(terminal_output).to_contain_text("Code submitted securely. Waiting for execution...", timeout=5000)
    
    # Wait for the C++ program to prompt for input
    # The default code says "Enter your name: "
    expect(terminal_output).to_contain_text("Enter your name: ", timeout=15000)
    
    # 5. Simulate User typing into the stdin field and pressing Enter
    terminal_input = page.locator("#terminalInput")
    expect(terminal_input).not_to_be_disabled()
    
    terminal_input.fill("PlaywrightBot")
    terminal_input.press("Enter")
    
    # 6. Validate the final output and clean shutdown
    expect(terminal_output).to_contain_text("Hello, PlaywrightBot! Welcome to the Sandbox.", timeout=5000)
    expect(terminal_output).to_contain_text("[Process exited with code 0]", timeout=5000)
    
    # Ensure it returns to disconnected state for the next run
    expect(page.locator("#connectionStatus")).to_have_text("Disconnected")
    expect(page.locator("#exeBtn")).to_have_text("Execute")
    expect(terminal_input).to_be_disabled()
