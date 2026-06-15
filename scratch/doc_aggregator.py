import os
import json

def get_all_docs(root_dir):
    docs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # exclude hidden dirs, venv, node_modules
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != 'node_modules']
        
        for file in filenames:
            if file.endswith('.md') or file.endswith('.txt'):
                filepath = os.path.join(dirpath, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Ignore archived files
                        if "[ARCHIVED - CONTENT CLEANED UP]" not in content:
                            # Skip empty files
                            if content.strip():
                                docs.append({
                                    "filepath": filepath,
                                    "filename": file,
                                    "content": content
                                })
                except Exception as e:
                    pass
    return docs

if __name__ == "__main__":
    root_directory = r"e:\Cores of ACE\polyglot-microservices-platform"
    all_docs = get_all_docs(root_dir=root_directory)
    
    output_path = os.path.join(root_directory, "scratch", "aggregated_docs.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_docs, f, indent=2)
        
    print(f"Aggregated {len(all_docs)} active document files into {output_path}")
