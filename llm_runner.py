import warnings
import sys, asyncio
if sys.platform == 'win32':
    warnings.filterwarnings('ignore', category=ResourceWarning)
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import re
from datetime import datetime
import json

from playwright.async_api import async_playwright, Page, Frame, Locator

# =========================
# Utils
# =========================

COMMON_ARGS = ["--disable-blink-features=AutomationControlled"]

def sanitize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

def clean_text(text: str) -> str:
    """Remove icons, emojis, and extra whitespace."""
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def frames_in_read_order(page: Page) -> List[Frame]:
    frs = [page.main_frame]
    for f in page.frames:
        if f is not page.main_frame:
            frs.append(f)
    return frs

# =========================
# Element finders
# =========================

async def find_input(page: Page, input_selector: Optional[str]) -> Locator:
    """Find the chat input."""
    candidates = [
        "textarea",
        "div[contenteditable='true']",
        "input[type='text']",
        "[aria-label*='message' i]",
        "#prompt-textarea",
    ]
    
    for fr in frames_in_read_order(page):
        try:
            loc = fr.get_by_role("textbox").first
            await loc.wait_for(state="visible", timeout=5000)
            return loc
        except:
            pass
        
        for sel in candidates:
            try:
                loc = fr.locator(sel).first
                await loc.wait_for(state="visible", timeout=1000)
                return loc
            except:
                continue
    
    raise RuntimeError(" Input field not found")

# =========================
# Browser context
# =========================

async def launch_persistent(user_data_dir: Path, headless: bool):
    """Launch browser with persistent profile."""
    user_data_dir.mkdir(parents=True, exist_ok=True)
    abs_path = user_data_dir.absolute()
    
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=str(abs_path),
        headless=headless,
        locale="en-US",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
        viewport={"width": 1366, "height": 900},
        args=COMMON_ARGS,
        ignore_https_errors=True,
    )
    return pw, context

# =========================
# Core flows
# =========================

async def cmd_setup(llm: Dict[str, Any]) -> Dict[str, Any]:
    """Setup: User logs in once."""
    name = llm["name"]
    url = llm["url"]

    profile_dir = Path(f"profiles/{sanitize_name(name)}").absolute()

    print(f"\n{'='*72}\nSETUP: {name}\n{'='*72}")
    print(f"🔍 Profile directory: {profile_dir}")
    
    pw, ctx = await launch_persistent(profile_dir, headless=False)
    page = await ctx.new_page()
    
    try:
        print(f"Opening {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        print("\n Log in to the service.")
        print("   Press ENTER when you see the chat interface.\n")
        input()
        state_path = profile_dir / "storage_state.json"
        await ctx.storage_state(path=str(state_path))
        print(f" Saved storage state to: {state_path}")
        
        print(" Setup complete. Profile saved.")
        print(await page.context.cookies())
        print(await page.evaluate("Object.keys(localStorage)"))
        return {**llm, "profile_dir": str(profile_dir)}
    
    finally:
        await page.wait_for_timeout(2000)
        await ctx.close()
        await pw.stop()
        

async def send_prompt(page: Page, llm: Dict[str, Any], prompt: str) -> Optional[str]:
    """Send prompt and get response. Returns response text or None."""
    
    try:
        inp = await find_input(page, llm.get("input_selector"))
        await inp.click()
        await page.keyboard.type(prompt, delay=30)
        
        await page.wait_for_timeout(300)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(100)  # WAIT between presses
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(100)
        await page.keyboard.press("Enter")
        
        print("   Waiting for response...")
        wait_time = llm.get("wait_time", 10000)
        await page.wait_for_timeout(wait_time)
        
        response_sel = llm.get("response_selector", ".markdown")
        last = page.locator(response_sel).last
        text = (await last.inner_text()).strip()
        
        if text and len(text) > 1:
            cleaned = clean_text(text)
            print(f" Got response ({len(cleaned)} chars)")
            return cleaned
        else:
            print("   No response text found")
            return None
            
    except Exception as e:
        print(f"   Error: {e}")
        return None

def save_response(llm_name: str, prompt: str, response: str, honeypot_name: str = None):
    """Save response to file."""
    output_dir = Path("responses")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if honeypot_name:
        honeypot_dir = output_dir / sanitize_name(honeypot_name)
        honeypot_dir.mkdir(exist_ok=True)
        filename = f"{sanitize_name(llm_name)}_{timestamp}.txt"
        filepath = honeypot_dir / filename
    else:
        filename = f"{sanitize_name(llm_name)}_{timestamp}.txt"
        filepath = output_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Provider: {llm_name}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        if honeypot_name:
            f.write(f"Honeypot: {honeypot_name}\n")
        f.write(f"Prompt: {prompt}\n")
        f.write(f"{'-'*72}\n")
        f.write(f"Response:\n{response}\n")
    
    print(f"   Saved to: {filepath}")

async def cmd_test(llm: Dict[str, Any], prompt: str, save: bool = True, honeypot_name: str = None) -> bool:
    """Test LLM with a prompt."""
    name = llm["name"]
    url = llm["url"]
    profile_dir = Path(f"profiles/{sanitize_name(name)}").absolute()
    state_path = profile_dir / "storage_state.json"

    print(f"\n{'='*72}\nTEST: {name}\n{'='*72}")

    if not state_path.exists():
        print(" No storage state found. Run 'setup' first.")
        return False

    pw = await async_playwright().start()
    
    # Try headless first
    try:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=str(state_path),
            locale="en-US",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
            viewport={"width": 1366, "height": 900},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        
        print(f"Loading {url} (headless)...")
        await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        response = await send_prompt(page, llm, prompt)
        
        if response:
            if save:
                save_response(name, prompt, response, honeypot_name)
            return True
            
        print("  ↪ Trying headful mode...")
        
    except Exception as e:
        print(f"   Headless failed: {e}")
    
    finally:
        await context.close()
        await browser.close()

    # Try headful if headless failed
    try:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=str(state_path),
            locale="en-US",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
            viewport={"width": 1366, "height": 900},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        
        await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        response = await send_prompt(page, llm, prompt)
        
        if response:
            if save:
                save_response(name, prompt, response, honeypot_name)
            return True
        
        return False
        
    finally:
        await context.close()
        await browser.close()
        await pw.stop()

async def cmd_batch(llm: Dict[str, Any], prompts_file: str, delay: int = 5) -> Dict[str, Any]:
    """Run batch of prompts through one LLM."""
    name = llm["name"]
    url = llm["url"]
    profile_dir = Path(f"profiles/{sanitize_name(name)}").absolute()

    print(f"\n{'='*72}\nBATCH TEST: {name}\n{'='*72}")

    if not profile_dir.exists():
        print(" No profile found. Run 'setup' first.")
        return {"success": 0, "failed": 0, "total": 0}

    # Load prompts (support both JSON and YAML)
    with open(prompts_file, "r", encoding="utf-8") as f:
        if prompts_file.endswith('.json'):
            data = json.load(f)
        else:
            data = yaml.safe_load(f)
    
    # Handle different JSON structures
    if "honeypots" in data:
        # Standard format: {"honeypots": [{"name": "...", "prompts": [...]}, ...]}
        honeypots = [(h.get("name", f"honeypot_{i}"), h.get("prompts", [])) 
                     for i, h in enumerate(data["honeypots"], 1)]
    elif isinstance(data, dict) and all(isinstance(v, list) for v in data.values()):
        # User's format: {"persona_name": ["prompt1", "prompt2", ...], ...}
        honeypots = list(data.items())
    elif isinstance(data, list):
        # Array format: [{"name": "...", "prompts": [...]}, ...]
        honeypots = [(h.get("name", f"honeypot_{i}"), h.get("prompts", [])) 
                     for i, h in enumerate(data, 1)]
    else:
        print(" Unrecognized JSON format")
        return {"success": 0, "failed": 0, "total": 0}
    
    print(f" Loaded {len(honeypots)} honeypots")
    total_prompts = sum(len(prompts) for _, prompts in honeypots)
    print(f" Total prompts: {total_prompts}")
    
    # Launch browser once and keep it open
    pw, ctx = await launch_persistent(profile_dir, headless=True)
    page = await ctx.new_page()
    
    success_count = 0
    failed_count = 0
    
    try:
        print(f"Loading {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        
        # Process each honeypot
        for hp_idx, (hp_name, prompts) in enumerate(honeypots, 1):
            
            print(f"\n{'─'*72}")
            print(f" Honeypot {hp_idx}/{len(honeypots)}: {hp_name} ({len(prompts)} prompts)")
            print(f"{'─'*72}")
            
            for p_idx, prompt in enumerate(prompts, 1):
                print(f"\n[{hp_idx}.{p_idx}] Sending prompt...")
                print(f"  {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
                
                response = await send_prompt(page, llm, prompt)
                
                if response:
                    save_response(name, prompt, response, hp_name)
                    success_count += 1
                else:
                    failed_count += 1
                
                # Delay between prompts
                if p_idx < len(prompts):
                    print(f"  Waiting {delay}s before next prompt...")
                    await page.wait_for_timeout(delay * 1000)
            
            # Longer delay between honeypots
            if hp_idx < len(honeypots):
                print(f"\n  Waiting {delay * 2}s before next honeypot...")
                await page.wait_for_timeout(delay * 2000)
        
        print(f"\n{'='*72}")
        print(f" Batch complete for {name}")
        print(f"   Success: {success_count}/{total_prompts}")
        print(f"   Failed: {failed_count}/{total_prompts}")
        print(f"{'='*72}")
        
    except Exception as e:
        print(f" Batch failed: {e}")
    
    finally:
        await page.wait_for_timeout(2000)
        await ctx.close()
        await pw.stop()
    
    return {
        "llm": name,
        "success": success_count,
        "failed": failed_count,
        "total": total_prompts
    }

# =========================
# CLI
# =========================

async def main():
    parser = argparse.ArgumentParser(description="Simple LLM browser automation")
    parser.add_argument("command", choices=["setup", "test", "setup-all", "test-all", "batch", "batch-all"])
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--name", help="Run for specific provider")
    parser.add_argument("--prompt", default="Hello, this is a test.")
    parser.add_argument("--prompts", default="prompts.json", help="JSON or YAML file with honeypots and prompts")
    parser.add_argument("--delay", type=int, default=5, help="Delay between prompts in seconds")
    parser.add_argument("--no-save", action="store_true", help="Don't save responses")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        cfg = yaml.safe_load(f)

    llms: List[Dict[str, Any]] = cfg.get("playwright_llms", [])
    
    if args.name:
        llms = [x for x in llms if x.get("name") == args.name]
        if not llms:
            print(f" No provider named '{args.name}'")
            return

    if args.command in ("setup", "setup-all"):
        updated = []
        for llm in llms:
            result = await cmd_setup(llm)
            updated.append(result)
        
        cfg["playwright_llms"] = updated
        with open(args.config, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        print("\n✓ Config updated")

    elif args.command in ("test", "test-all"):
        results = {}
        for llm in llms:
            ok = await cmd_test(llm, args.prompt, save=not args.no_save)
            results[llm["name"]] = ok

        print(f"\n{'='*72}\nSUMMARY\n{'='*72}")
        working = [k for k, v in results.items() if v]
        failed = [k for k, v in results.items() if not v]
        
        print(f" Working: {len(working)}/{len(results)}")
        for k in working:
            print(f"  • {k}")
        
        if failed:
            print(f"\n Failed: {len(failed)}/{len(results)}")
            for k in failed:
                print(f"  • {k}")
    
    elif args.command in ("batch", "batch-all"):
        if not Path(args.prompts).exists():
            print(f" Prompts file not found: {args.prompts}")
            return
        
        all_results = []
        
        for llm in llms:
            result = await cmd_batch(llm, args.prompts, args.delay)
            all_results.append(result)
        
        # Summary
        print(f"\n{'='*72}")
        print("BATCH SUMMARY")
        print(f"{'='*72}")
        
        for res in all_results:
            print(f"\n{res['llm']}:")
            print(f"  Success: {res['success']}/{res['total']}")
            print(f"   Failed: {res['failed']}/{res['total']}")
        
        # Save summary
        summary_file = Path("responses") / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n Summary saved to: {summary_file}")

if __name__ == "__main__":
    asyncio.run(main())