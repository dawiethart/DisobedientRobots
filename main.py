import asyncio
import yaml
import json
from datetime import datetime
from pathlib import Path
from api_handler import APIHandler
from playwright_handler import PlaywrightHandler

async def save_results(persona, model, results):
    """Save results to JSON file"""
    output_dir = Path('results') / datetime.now().strftime('%Y-%m-%d')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = output_dir / f'{persona}_{model}_{datetime.now().strftime("%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"   Saved to {filename}")

async def run_persona(persona_name, prompts, config, api_handler, playwright_handler):
    """Run all LLMs for one persona"""
    print(f"\n{'='*70}")
    print(f"PERSONA: {persona_name}")
    print(f"{'='*70}")
    
    # API LLMs (5 models)
    api_models = ['openai', 'anthropic', 'gemini', 'perplexity', 'mistral']
    
    for model in api_models:
        print(f"\n[API] Running {model.upper()}...")
        try:
            results = await api_handler.run_batch(
                model, 
                prompts, 
                persona_name,
                delay=config['timing']['between_prompts']
            )
            await save_results(persona_name, model, results)
            print(f"  ✓ Completed {model}")
        except Exception as e:
            print(f"  ✗ Error with {model}: {e}")
        
        # Wait between LLMs
        print(f"   Waiting {config['timing']['between_llms']}s...")
        await asyncio.sleep(config['timing']['between_llms'])
    
    # Playwright LLMs (8 models)
    for llm_config in config['playwright_llms']:
        print(f"\n[PLAYWRIGHT] Running {llm_config['name'].upper()}...")
        try:
            results = await playwright_handler.run_batch(
                llm_config,
                prompts,
                persona_name,
                delay=config['timing']['between_prompts']
            )
            await save_results(persona_name, llm_config['name'], results)
            print(f"  Completed {llm_config['name']}")
        except Exception as e:
            print(f"  Error with {llm_config['name']}: {e}")
        
        # Wait between LLMs
        print(f" Waiting {config['timing']['between_llms']}s...")
        await asyncio.sleep(config['timing']['between_llms'])

async def main():
    start_time = datetime.now()
    
    print("="*70)
    print("HONEYPOT STUDY - AUTOMATED LLM QUERYING OF HONEYPOTS")
    print("="*70)
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Load configuration
    print("\n Loading configuration...")
    with open('config.yaml', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    with open('prompts.json', encoding='utf-8') as f:
        prompts_by_persona = json.load(f)
    
    print(f" Loaded {len(prompts_by_persona)} personas")
    print(f" Total prompts: {sum(len(p) for p in prompts_by_persona.values())}")
    print(f" API LLMs: 5 (OpenAI, Anthropic, Gemini, Perplexity, Mistral)")
    print(f" Playwright LLMs: {len(config['playwright_llms'])}")
    print(f" Total LLMs: {5 + len(config['playwright_llms'])}")
    
    # Initialize handlers
    print("\n Initializing handlers...")
    api_handler = APIHandler(config)
    print(" API handler ready")
    
    playwright_handler = PlaywrightHandler(config)
    await playwright_handler.initialize()
    print(" Playwright handler ready")
    
    try:
        # Run each persona sequentially
        persona_count = 0
        for persona_name, prompts in prompts_by_persona.items():
            persona_count += 1
            print(f"\n\n{'#'*70}")
            print(f"# PERSONA {persona_count}/{len(prompts_by_persona)}")
            print(f"{'#'*70}")
            
            await run_persona(persona_name, prompts, config, api_handler, playwright_handler)
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "="*70)
        print("STUDY COMPLETE!")
        print("="*70)
        print(f"Start Time:    {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:      {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:      {duration}")
        print(f"Personas:      {len(prompts_by_persona)}")
        print(f"Total Queries: {len(prompts_by_persona) * 10 * 13}")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user!")
    except Exception as e:
        print(f"\n\n Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n Cleaning up...")
        await playwright_handler.close()
        print(" Done!")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")