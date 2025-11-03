import asyncio
from playwright.async_api import async_playwright
import json
import yaml

async def test_selectors(page, llm_config):
    """Test if selectors work on the current page"""
    print(f"\n  Testing selectors...")
    
    results = {
        'input': False,
        'submit': False,
        'response': False
    }
    
    # Test input selector
    try:
        input_elem = await page.wait_for_selector(llm_config['input_selector'], timeout=3000)
        if input_elem:
            results['input'] = True
            print(f"  ✓ Input selector works: {llm_config['input_selector']}")
    except:
        print(f"  ✗ Input selector FAILED: {llm_config['input_selector']}")
    
    # Test submit selector
    try:
        submit_elem = await page.wait_for_selector(llm_config['submit_selector'], timeout=3000)
        if submit_elem:
            results['submit'] = True
            print(f"  ✓ Submit selector works: {llm_config['submit_selector']}")
    except:
        print(f"  ✗ Submit selector FAILED: {llm_config['submit_selector']}")
    
    # Test response selector (might not exist yet, that's OK)
    try:
        response_elem = await page.query_selector(llm_config['response_selector'])
        if response_elem:
            results['response'] = True
            print(f"  ✓ Response selector works: {llm_config['response_selector']}")
        else:
            print(f"  ⚠  Response selector not found (might appear after first query): {llm_config['response_selector']}")
    except:
        print(f"  ⚠  Response selector not found (might appear after first query): {llm_config['response_selector']}")
    
    return results

async def find_selector_interactive(page, selector_type):
    """Help user find the correct selector interactively"""
    print(f"\n  🔍 Finding {selector_type} selector...")
    print(f"  Options:")
    print(f"    1. Use browser DevTools (Right-click → Inspect)")
    print(f"    2. I'll try common selectors automatically")
    
    choice = input(f"  Choose (1/2) or press Enter to skip: ").strip()
    
    if choice == '2':
        # Try common selectors based on type
        if selector_type == 'input':
            common = [
                'textarea',
                'input[type="text"]',
                'div[contenteditable="true"]',
                '[placeholder*="Ask"]',
                '[placeholder*="ask"]',
                '[aria-label*="message"]',
                '[aria-label*="Message"]',
                '.input-box',
                '#prompt-textarea',
                '.ql-editor'
            ]
        elif selector_type == 'submit':
            common = [
                'button[type="submit"]',
                'button[aria-label*="Send"]',
                'button[aria-label*="Submit"]',
                'button:has-text("Send")',
                '[data-testid="send-button"]',
                '.send-button',
                '[aria-label*="send"]'
            ]
        else:  # response
            common = [
                '.markdown',
                '.message',
                '.response',
                '.answer',
                '[class*="message"]',
                '[class*="response"]',
                '[class*="answer"]',
                '.prose',
                'article'
            ]
        
        print(f"\n  Trying common selectors...")
        for selector in common:
            try:
                elem = await page.wait_for_selector(selector, timeout=1000)
                if elem:
                    print(f"  ✅ Found: {selector}")
                    return selector
            except:
                pass
        
        print(f"  ❌ None of the common selectors worked")
    
    print(f"\n  Enter the selector manually (or press Enter to use default):")
    manual_selector = input(f"  Selector: ").strip()
    
    return manual_selector if manual_selector else None

async def save_cookies_for_llm(llm_name, llm_config):
    """Manually login and save cookies for a specific LLM, with selector testing"""
    print(f"\n{'='*70}")
    print(f"Setting up: {llm_name.upper()}")
    print(f"{'='*70}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        context = await browser.new_context()
        page = await context.new_page()
        
        # Enable console logging for debugging
        page.on('console', lambda msg: print(f"  [Browser Console] {msg.text}"))
        
        print(f"Opening {llm_config['url']}...")
        try:
            await page.goto(llm_config['url'], wait_until='networkidle', timeout=60000)
        except:
            print(f"  ⚠️  Timeout/error loading page, but continuing...")
            await page.wait_for_timeout(3000)
        
        print(f"\n📱 INSTRUCTIONS FOR {llm_name.upper()}")
        print("=" * 70)
        print("1. Complete the login process in the browser (if needed)")
        print("2. Make sure you're fully logged in and can see the chat interface")
        print("3. For search engines: just wait on the page")
        print("4. Press ENTER here to test selectors...")
        print("=" * 70)
        
        input()  # Wait for user to login
        
        # Test selectors
        print(f"\n{'='*70}")
        print(f"TESTING SELECTORS FOR {llm_name.upper()}")
        print(f"{'='*70}")
        
        test_results = await test_selectors(page, llm_config)
        
        # If any selector failed, offer to find new ones
        if not all(test_results.values()):
            print(f"\n⚠️  Some selectors don't work!")
            print(f"Would you like to find correct selectors? (y/n)")
            fix = input().strip().lower()
            
            if fix == 'y':
                new_config = llm_config.copy()
                
                if not test_results['input']:
                    print(f"\n🔍 Finding INPUT selector...")
                    print(f"Current: {llm_config['input_selector']}")
                    new_selector = await find_selector_interactive(page, 'input')
                    if new_selector:
                        new_config['input_selector'] = new_selector
                
                if not test_results['submit']:
                    print(f"\n🔍 Finding SUBMIT button selector...")
                    print(f"Current: {llm_config['submit_selector']}")
                    new_selector = await find_selector_interactive(page, 'submit')
                    if new_selector:
                        new_config['submit_selector'] = new_selector
                
                if not test_results['response']:
                    print(f"\n🔍 Finding RESPONSE selector...")
                    print(f"Current: {llm_config['response_selector']}")
                    new_selector = await find_selector_interactive(page, 'response')
                    if new_selector:
                        new_config['response_selector'] = new_selector
                
                # Test new selectors
                print(f"\n  Testing new selectors...")
                new_results = await test_selectors(page, new_config)
                
                if sum(new_results.values()) > sum(test_results.values()):
                    print(f"\n  ✅ New selectors are better!")
                    llm_config.update(new_config)
                else:
                    print(f"\n  ⚠️  New selectors didn't improve things")
        else:
            print(f"\n✅ All selectors work!")
        
        # Save cookies
        cookie_file = f'cookies_{llm_name}.json'
        await context.storage_state(path=cookie_file)
        print(f"\n✓ Cookies saved to {cookie_file}")
        
        await browser.close()
        
        return llm_config

async def main():
    print("="*70)
    print("PLAYWRIGHT COOKIE & SELECTOR SETUP")
    print("="*70)
    print("This script will:")
    print("  1. Help you login to each LLM service")
    print("  2. Test if the CSS selectors work correctly")
    print("  3. Help you find correct selectors if they don't work")
    print("  4. Save authentication cookies for automation")
    print("="*70)
    
    # Load current config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    llms = config['playwright_llms']
    
    print(f"\nYou will set up {len(llms)} services:")
    for i, llm in enumerate(llms, 1):
        print(f"  {i}. {llm['name']} - {llm['url']}")
    
    print("\n⚠️  NOTE: Some services may not require login (DuckDuckGo, Brave)")
    print("   Just press ENTER after the page loads for these.")
    
    print("\nPress ENTER to start...")
    input()
    
    updated_configs = []
    
    for llm in llms:
        updated_config = await save_cookies_for_llm(llm['name'], llm)
        updated_configs.append(updated_config)
    
    # Check if any selectors were updated
    config_changed = False
    for i, llm in enumerate(llms):
        if llm != updated_configs[i]:
            config_changed = True
            break
    
    if config_changed:
        print("\n" + "="*70)
        print("SELECTORS WERE UPDATED!")
        print("="*70)
        print("Would you like to save the updated selectors to config.yaml? (y/n)")
        save = input().strip().lower()
        
        if save == 'y':
            config['playwright_llms'] = updated_configs
            with open('config.yaml', 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print("✓ config.yaml updated with new selectors!")
        else:
            print("⚠️  Selectors NOT saved. You can manually update config.yaml")
            print("\nUpdated selectors:")
            for llm in updated_configs:
                if llm != llms[updated_configs.index(llm)]:
                    print(f"\n{llm['name']}:")
                    print(f"  input_selector: {llm['input_selector']}")
                    print(f"  submit_selector: {llm['submit_selector']}")
                    print(f"  response_selector: {llm['response_selector']}")
    
    print("\n" + "="*70)
    print("✓ ALL SETUP COMPLETE!")
    print("="*70)
    print(f"✓ {len(llms)} cookie files saved")
    if config_changed and save == 'y':
        print("✓ config.yaml updated with working selectors")
    print("\nYou can now run: python main.py")
    print("="*70)

if __name__ == '__main__':
    asyncio.run(main())