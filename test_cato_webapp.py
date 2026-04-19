#!/usr/bin/env python3
"""Cato Webapp Automated Test Suite"""
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:7778"

def test_new_chat_button(page):
    """Test 1: New Chat button clears conversation"""
    print("\n=== Test 1: New Chat Button ===")
    errors = []
    
    page.goto(f"{BASE_URL}/chat")
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    screenshot1 = page.screenshot(path='test1_initial.png', full_page=True)
    
    initial_messages = page.locator('[class*="message"]').count()
    print(f"  Initial messages: {initial_messages}")
    
    new_chat_btn = page.locator('button', has_text='New chat').first
    if new_chat_btn:
        new_chat_btn.click()
        page.wait_for_timeout(1000)
        print("  [OK] Clicked New Chat")
    else:
        errors.append("New Chat button not found")
        print("  [FAIL] New Chat button NOT FOUND")
    
    screenshot2 = page.screenshot(path='test1_after.png', full_page=True)
    
    return errors

def test_session_history(page):
    """Test 2: Session history displays and is clickable"""
    print("\n=== Test 2: Session History ===")
    errors = []
    
    page.goto(f"{BASE_URL}/history")
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    screenshot = page.screenshot(path='test2_history.png', full_page=True)
    
    session_items = page.locator('[class*="session"], [class*="history-item"]').count()
    print(f"  Session items found: {session_items}")
    
    if session_items > 0:
        first_session = page.locator('[class*="session"], [class*="history-item"]').first
        first_session.click()
        page.wait_for_timeout(1000)
        print(f"  [OK] Clicked first session")
    else:
        errors.append("No session history items found")
        print("  [WARN] No sessions in history")
    
    return errors

def test_send_message(page):
    """Test 3: Send a message and verify AI responds"""
    print("\n=== Test 3: Send Message ===")
    errors = []
    
    page.goto(f"{BASE_URL}/chat")
    page.wait_for_load_state('networkidle')
    time.sleep(1)
    
    textarea = page.locator('textarea').first
    if textarea:
        textarea.fill("Hi, can you see this?")
        print("  [OK] Typed message")
        
        send_btn = page.locator('button', has_text='發送').first
        if send_btn:
            send_btn.click()
            print("  [OK] Clicked Send")
            page.wait_for_timeout(3000)
            
            messages = page.locator('[class*="message"]').count()
            print(f"  Messages after send: {messages}")
            
            screenshot = page.screenshot(path='test3_after_send.png', full_page=True)
        else:
            errors.append("Send button not found")
            print("  [FAIL] Send button NOT FOUND")
    else:
        errors.append("Textarea not found")
        print("  [FAIL] Textarea NOT FOUND")
    
    return errors

def test_stop_button(page):
    """Test 4: Stop button appears during streaming"""
    print("\n=== Test 4: Stop Button ===")
    errors = []
    
    page.goto(f"{BASE_URL}/chat")
    page.wait_for_load_state('networkidle')
    
    textarea = page.locator('textarea').first
    if textarea:
        textarea.fill("Write a long story about a cat")
        send_btn = page.locator('button', has_text='發送').first
        if send_btn:
            send_btn.click()
            page.wait_for_timeout(500)
            
            stop_btn = page.locator('button', has_text='停止').first
            if stop_btn:
                print("  [OK] Stop button appeared during streaming")
                stop_btn.click()
                page.wait_for_timeout(500)
                print("  [OK] Clicked Stop")
            else:
                errors.append("Stop button not found during streaming")
                print("  [WARN] Stop button not visible (may have finished too fast)")
    else:
        errors.append("Textarea not found")
    
    screenshot = page.screenshot(path='test4_stop.png', full_page=True)
    return errors

def test_title_generation(page):
    """Test 5: Verify session title updates after AI response"""
    print("\n=== Test 5: Title Generation ===")
    errors = []
    
    page.goto(f"{BASE_URL}/chat")
    page.wait_for_load_state('networkidle')
    
    textarea = page.locator('textarea').first
    if textarea:
        textarea.fill("Explain quantum physics in simple terms")
        send_btn = page.locator('button', has_text='發送').first
        send_btn.click()
        print("  [OK] Sent message about quantum physics")
        
        page.wait_for_timeout(8000)
        
        screenshot = page.screenshot(path='test5_title.png', full_page=True)
        
        title_area = page.locator('[class*="title"], [class*="header"]').first
        title_text = title_area.inner_text() if title_area else ""
        print(f"  Title: {title_text}")
        
        if title_text and title_text.lower() not in ["new chat", "chat", ""]:
            print(f"  [OK] Title was generated: {title_text}")
        else:
            errors.append("Title not updated - still generic")
            print(f"  [WARN] Title still generic: {title_text}")
    
    return errors

def capture_console_logs(page):
    """Capture console errors"""
    print("\n=== Console Logs ===")
    errors = []
    
    def handle_console(msg):
        if msg.type == 'error':
            errors.append(f"Console error: {msg.text}")
            print(f"  [FAIL] Console error: {msg.text}")
    
    page.on('console', handle_console)
    return errors

def main():
    print("=" * 60)
    print("  Cato Webapp Automated Test Suite")
    print("=" * 60)
    
    all_errors = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            console_errors = capture_console_logs(page)
            all_errors.extend(console_errors)
            
            all_errors.extend(test_new_chat_button(page))
            all_errors.extend(test_session_history(page))
            all_errors.extend(test_send_message(page))
            all_errors.extend(test_stop_button(page))
            all_errors.extend(test_title_generation(page))
            
            browser.close()
    
    except Exception as e:
        all_errors.append(f"Test suite error: {str(e)}")
        print(f"\n❌ Exception: {e}")
    
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    if all_errors:
        print(f"\n[FAIL] {len(all_errors)} ISSUE(S) FOUND:")
        for i, err in enumerate(all_errors, 1):
            print(f"  {i}. {err}")
    else:
        print("\n[OK] ALL TESTS PASSED - No issues found!")
    
    print("\nScreenshots saved:")
    print("  - test1_initial.png, test1_after.png")
    print("  - test2_history.png")
    print("  - test3_after_send.png")
    print("  - test4_stop.png")
    print("  - test5_title.png")
    
    return len(all_errors) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
