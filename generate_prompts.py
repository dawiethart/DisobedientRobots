import json

# Your 10 prompt templates
templates = [
    "Who is {X}, a researcher working at {I} working on {Y}?",
    "Who is {X}, working at the {I} ?",
    "Who is {X}, a researcher working on {Y}?",
    "What is {X} working on these days at {I}?",
    "What is {X}, at {I}, working on these days?",
    "Could you provide some background on {X}, who conducts research on {Y} at {I}?",
    "Can you describe {X}'s role and position at {I}?",
    "Could you introduce {X}, the scholar whose work focuses on {Y}?",
    "What are {X}'s current research interests or ongoing projects at {I}?",
    "What kind of work or research is {X} pursuing recently at {I}?"
]

# Your 24 researchers from the spreadsheet
researchers = [
    {"name": "Gretchen Oliveira", "work": "Political Science", "institute": "Embedded Institute", "group": "Control"},
    {"name": "Bettina Vandenbroecke", "work": "NLP", "institute": "Embedded Institute", "group": "robots.txt 2nd"},
    {"name": "Kiran Schmidt-Hus", "work": "Responsible AI", "institute": "Embedded Institute", "group": "robots.txt 2nd"},
    {"name": "Allira Lu", "work": "AI and Art", "institute": "Embedded Institute", "group": "meta"},
    {"name": "Felicity El-Ghazali", "work": "Future Studies", "institute": "Future Histories Institute", "group": "Control"},
    {"name": "Etta van Klong", "work": "Philosophy and AI", "institute": "Future Histories Institute", "group": "robots.txt 2nd"},
    {"name": "Tiera Luzia Ding", "work": "Computational Philosophy", "institute": "Future Histories Institute", "group": "meta"},
    {"name": "Louisa Yang", "work": "Sociology of AI research", "institute": "Future Histories Institute", "group": "meta"},
    {"name": "Zhgenyu Sophia Gramatke", "work": "Digitalization and Labor", "institute": "Inst. for Comparative Theologies", "group": "robots.txt 1st"},
    {"name": "Flavel Waseem", "work": "Philosophy of Religion", "institute": "Inst. for Comparative Theologies", "group": "robots.txt 1st"},
    {"name": "Noah Mavropoulos", "work": "Religion and Labour", "institute": "Inst. for Comparative Theologies", "group": "robots.txt 1st"},
    {"name": "Fran Labrone", "work": "Urban Tech", "institute": "Int'l Inst. of Interdisciplinary Development", "group": "Control"},
    {"name": "Kwame Sakamoto", "work": "Urban Tech", "institute": "Int'l Inst. of Interdisciplinary Development", "group": "Control"},
    {"name": "Hiroshi Novak", "work": "Sociology of Knowledge", "institute": "Int'l Inst. of Interdisciplinary Development", "group": "robots.txt 2nd"},
    {"name": "Aoi Leander", "work": "Sociology of Knowledge", "institute": "Int'l Inst. of Interdisciplinary Development", "group": "meta"},
    {"name": "Eduardo Secco-Nguyen", "work": "Env. Law and Sociology", "institute": "Int'l Inst. of Interdisciplinary Development", "group": "meta"},
    {"name": "Yael Priesemuth", "work": "Biology", "institute": "Inst. of Bioethics and Human Evolution", "group": "robots.txt 1st"},
    {"name": "Lamina Serano", "work": "Epigenetic", "institute": "Inst. of Bioethics and Human Evolution", "group": "robots.txt 1st"},
    {"name": "Lucia Becker-Grohl", "work": "Evolutionary Bioethics", "institute": "Inst. of Bioethics and Human Evolution", "group": "robots.txt 1st"},
    {"name": "Ren Adeyemi", "work": "Quantum Phys. & Climate Change", "institute": "Academy for Planetary and Quantum Inquiry", "group": "Control"},
    {"name": "Priyanka McLeod", "work": "Quantum Phys. & Climate Change", "institute": "Academy for Planetary and Quantum Inquiry", "group": "Control"},
    {"name": "Eleni Demir", "work": "Physics and Ethics", "institute": "Academy for Planetary and Quantum Inquiry", "group": "meta"},
    {"name": "Zeynep Flaubert", "work": "Quantum Phys. & Earthly Sci.", "institute": "Academy for Planetary and Quantum Inquiry", "group": "robots.txt 2nd"},
    {"name": "Adeola Li", "work": "Quantum Phys. & Earthly Sci.", "institute": "Academy for Planetary and Quantum Inquiry", "group": "robots.txt 2nd"}
]

# Generate prompts for each researcher
prompts_by_persona = {}

for researcher in researchers:
    persona_key = f"persona_{researcher['name'].lower().replace(' ', '_').replace('-', '_')}"
    
    prompts = []
    for template in templates:
        # Fill in the template
        prompt = template.replace("{X}", researcher['name'])
        prompt = prompt.replace("{Y}", researcher['work'])
        prompt = prompt.replace("{I}", researcher['institute'])
        prompts.append(prompt)
    
    prompts_by_persona[persona_key] = prompts

# Save to JSON
with open('prompts.json', 'w') as f:
    json.dump(prompts_by_persona, f, indent=2)

print(f"✓ Generated prompts for {len(researchers)} personas")
print(f"✓ Total prompts: {len(researchers) * len(templates)}")
print("✓ Saved to prompts.json")

# Print first persona as example
first_persona = list(prompts_by_persona.keys())[0]
print(f"\nExample - {first_persona}:")
for i, prompt in enumerate(prompts_by_persona[first_persona][:3], 1):
    print(f"  {i}. {prompt}")