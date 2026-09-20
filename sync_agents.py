import os
import shutil

# Configurations
SOURCE_DIR = "agents"
VSCODE_DIR = ".github/agents"
CURSOR_DIR = ".cursor/agents"

def setup_directories():
    for d in [SOURCE_DIR, VSCODE_DIR, CURSOR_DIR]:
        os.makedirs(d, exist_ok=True)

def sync_agents():
    print("Syncing AI agents to IDE directories...")
    
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
    # Process files inside the folder
    for filename in os.listdir(SOURCE_DIR):
        # Match your existing source naming convention
        if not filename.lower().endswith(".agent.md"):
            continue
            
        # Clean file names (removing spaces for predictable resource lookups)
        clean_name = filename.replace(" ", "-").lower()
        base_name = clean_name.replace(".agent.md", "")
        
        source_path = os.path.join(SOURCE_DIR, filename)
        
        # 1. Format for VS Code (Keep the native .agent.md markup format)
        vscode_dest = os.path.join(VSCODE_DIR, f"{base_name}.agent.md")
        try:
            shutil.copy2(source_path, vscode_dest)
        except Exception as e:
            print(f"Error copying to VS Code path: {e}")
            continue

        # 2. Format for Cursor (Convert extension wrapper down to standard fallback .md)
        cursor_dest = os.path.join(CURSOR_DIR, f"{base_name}.md")
        try:
            shutil.copy2(source_path, cursor_dest)
        except Exception as e:
            print(f"Error copying to Cursor path: {e}")
            continue

        print(f"Synced: {filename} -> {base_name}")
        files_processed += 1

    if files_processed == 0:
        print("Warning: No source '.agent.md' files were detected or compiled.")

if __name__ == "__main__":
    setup_directories()
    sync_agents()
    print("\nSync complete! Run 'git status' to verify.")
