import os
import yaml

# Configurations
SOURCE_DIR = "agents"  # Where you edit your agents
VSCODE_DIR = ".github/agents"
CURSOR_DIR = ".cursor/agents"

# Sample agents to initialize if directory is empty
DEFAULT_AGENTS = {
    "code-reviewer": {
        "description": "Reviews pull requests for performance, security, and styling.",
        "model": "claude-3-5-sonnet",
        "tools": ["edit", "search", "context"],
        "instructions": "# Code Reviewer\nAct as a Principal Engineer. Review code for bugs, logic flaws, and optimization opportunities."
    },
    "git-assistant": {
        "description": "Generates semantic commit messages and cleans up branch names.",
        "model": "gpt-4o",
        "tools": ["terminal", "context"],
        "instructions": "# Git Assistant\nInspect the staged changes or git diff. Generate clean Conventional Commits style messages."
    }
}

def setup_directories():
    for d in [SOURCE_DIR, VSCODE_DIR, CURSOR_DIR]:
        os.makedirs(d, exist_ok=True)

def initialize_samples():
    if not os.listdir(SOURCE_DIR):
        print(f"Initializing source agents in '{SOURCE_DIR}/'...")
        for name, data in DEFAULT_AGENTS.items():
            file_path = os.path.join(SOURCE_DIR, f"{name}.yml")
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, sort_keys=False, allow_unicode=True)

def sync_agents():
    print("Syncing AI agents to IDE directories...")
    
    # Clean output directories to avoid stale configurations
    for d in [VSCODE_DIR, CURSOR_DIR]:
        for f in os.listdir(d):
            if f.endswith(".md"):
                os.remove(os.path.join(d, f))

    # Process each source workflow yaml file
    for filename in os.listdir(SOURCE_DIR):
        if not filename.endswith((".yml", ".yaml")):
            continue
            
        base_name = os.path.splitext(filename)[0]
        source_path = os.path.join(SOURCE_DIR, filename)
        
        with open(source_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing {filename}: {e}")
                continue

        instructions = data.pop("instructions", "")
        
        # 1. Format for VS Code (Requires YAML Frontmatter + .agent.md extension)
        vscode_frontmatter = yaml.dump(data, sort_keys=False).strip()
        vscode_content = f"---\n{vscode_frontmatter}\n---\n\n{instructions}"
        vscode_dest = os.path.join(VSCODE_DIR, f"{base_name}.agent.md")
        with open(vscode_dest, "w", encoding="utf-8") as f:
            f.write(vscode_content)

        # 2. Format for Cursor / General Fallbacks (Clean Markdown, Metadata optional)
        cursor_content = f"# Agent: {data.get('name', base_name)}\n> {data.get('description', '')}\n\n{instructions}"
        cursor_dest = os.path.join(CURSOR_DIR, f"{base_name}.md")
        with open(cursor_dest, "w", encoding="utf-8") as f:
            f.write(cursor_content)

        print(f"Synced: {base_name}")

if __name__ == "__main__":
    setup_directories()
    initialize_samples()
    sync_agents()
    print("\nSync complete! Run 'git status' to see the updated configurations.")
