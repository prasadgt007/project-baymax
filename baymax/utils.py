import os

def load_skills(file_path: str = "skills.md") -> dict:
    """Parses skills.md and returns a dictionary of prompts."""
    skills = {}
    current_agent = None
    current_prompt = []
    
    # Resolve absolute path relative to project root
    # Since utils.py is in baymax/, and skills.md is now also in baymax/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, file_path)
    
    if not os.path.exists(full_path):
        return {}

    with open(full_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                # Save previous agent's prompt
                if current_agent:
                    skills[current_agent] = "\n".join(current_prompt).strip()
                
                # Start new agent
                current_agent = line.strip()[2:] # Remove "# "
                current_prompt = []
            elif current_agent:
                current_prompt.append(line)
                
    # Save the last one
    if current_agent:
        skills[current_agent] = "\n".join(current_prompt).strip()
        
    return skills

_SKILLS_CACHE: dict = {}

def get_skill(agent_name: str) -> str:
    """Helper to fetch a single agent's prompt."""
    global _SKILLS_CACHE
    if not _SKILLS_CACHE:
        _SKILLS_CACHE = load_skills()
    return _SKILLS_CACHE.get(agent_name, f"You are a helpful {agent_name}.")
