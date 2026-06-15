import os
import re

directories_to_scan = [
    r"e:\Cores of ACE\polyglot-microservices-platform",
    r"C:\Users\adnan\.gemini\antigravity\brain\05efde0d-dce1-4935-a2cc-be160a9e8bb2"
]

patterns_to_replace = [
    (re.compile(r"Discord-style", re.IGNORECASE), "Categorized Workspace"),
    (re.compile(r"Discord-Style", re.IGNORECASE), "Categorized Workspace"),
    (re.compile(r"Discord style", re.IGNORECASE), "Categorized Workspace"),
    (re.compile(r"Discord's", re.IGNORECASE), "the platform's"),
    (re.compile(r"Discord", re.IGNORECASE), "Categorized Workspace")
]

files_modified = 0

for directory in directories_to_scan:
    for root, _, files in os.walk(directory):
        if ".system_generated" in root or ".git" in root or "node_modules" in root:
            continue
        for file in files:
            if file.endswith((".md", ".html", ".txt")):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    for pattern, replacement in patterns_to_replace:
                        new_content = pattern.sub(replacement, new_content)
                    
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Cleaned: {filepath}")
                        files_modified += 1
                except Exception as e:
                    pass

print(f"Total files cleaned: {files_modified}")
