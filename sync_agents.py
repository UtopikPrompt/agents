import os
import shutil

# Configurations
SOURCE_DIR = "agents"
VSCODE_DIR = ".github/agents"
CURSOR_DIR = ".cursor/agents"
ROOT_AGENTS_FILE = "AGENTS.md"
ROOT_CLAUDE_FILE = "CLAUDE.md"

def setup_directories():
    for d in [SOURCE_DIR, VSCODE_DIR, CURSOR_DIR]:
        os.makedirs(d, exist_ok=True)

def sync_agents():
    print("Syncing AI agents to IDE and Claude configurations...")
    
    # Clean output directories to avoid stale configurations
    for d in [VSCODE_DIR, CURSOR_DIR]:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".md"):
                    try:
                        os.remove(os.path.join(d, f))
                    except Exception:
                        pass

    files_processed = 0
    compiled_markdown_content = "# Project Workflows & System Agents\n\n"

    # Process files inside the folder
    for filename in sorted(os.listdir(SOURCE_DIR)):
        if not filename.lower().endswith(".agent.md"):
            continue
            
        clean_name = filename.replace(" ", "-").lower()
        base_name = clean_name.replace(".agent.md", "")
        source_path = os.path.join(SOURCE_DIR, filename)
        
        # Read content for the root master files compilation
        with open(source_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            
        # Append to the consolidated root documentation layout
        compiled_markdown_content += f"## Agent Profile: {filename.replace('.agent.md', '')}\n\n{raw_content}\n\n---\n\n"

        # 1. Format for VS Code
        vscode_dest = os.path.join(VSCODE_DIR, f"{base_name}.agent.md")
        try:
            shutil.copy2(source_path, vscode_dest)
        except Exception as e:
            print(f"Error copying to VS Code path: {e}")
            continue

        # 2. Format for Cursor
        cursor_dest = os.path.join(CURSOR_DIR, f"{base_name}.md")
        try:
            shutil.copy2(source_path, cursor_dest)
        except Exception as e:
            print(f"Error copying to Cursor path: {e}")
            continue

        print(f"Synced: {filename} -> {base_name}")
        files_processed += 1

    if files_processed > 0:
        # Write out to the emerging industry standard root files
        with open(ROOT_AGENTS_FILE, "w", encoding="utf-8") as f:
            f.write(compiled_markdown_content)
        with open(ROOT_CLAUDE_FILE, "w", encoding="utf-8") as f:
            f.write(compiled_markdown_content)
        print(f"Generated root workspace profiles: {ROOT_AGENTS_FILE} & {ROOT_CLAUDE_FILE}")
    else:
        print("Warning: No source '.agent.md' files were detected or compiled.")

if __name__ == "__main__":
    setup_directories()
    sync_agents()
    print("\nSync complete! Run 'git status' to verify.")
