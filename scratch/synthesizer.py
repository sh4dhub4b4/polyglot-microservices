import json
import os

ROLE_MAPPING = {
    "Product Manager (PM) & Business Strategy": ["prd", "brs", "srs", "lean_canvas", "mvp_scope", "pricing", "personas", "journey", "roadmap", "timeline", "anatomy", "progress", "achievements"],
    "Backend & Systems Architect": ["architecture", "schema", "api", "data_dictionary", "gateway", "diagram", "tenant", "database"],
    "DevOps & Infrastructure Engineer": ["devops", "ci_cd", "k8s", "docker", "helm", "deploy", "pipeline"],
    "Security & Compliance Officer": ["compliance", "security", "threat", "auth", "identity", "rbac"],
    "QA & Testing Lead": ["testing", "validation", "test", "gauntlet"],
    "Frontend & UI/UX Designer": ["wireframe", "mockup", "frontend", "component", "gui", "ux"]
}

def categorize_doc(filename):
    name_lower = filename.lower()
    for role, keywords in ROLE_MAPPING.items():
        for kw in keywords:
            if kw in name_lower:
                return role
    return "General Documentation"

def synthesize_master_doc(json_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)
        
    categorized = {role: [] for role in ROLE_MAPPING.keys()}
    categorized["General Documentation"] = []
    
    for doc in docs:
        role = categorize_doc(doc['filename'])
        categorized[role].append(doc)
        
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write("# 📚 Polyglot Microservices Platform: Comprehensive Role-Based Master Document\n\n")
        out.write("> This master document synthesizes all active documentation across the repository, categorized by the roles responsible for them.\n\n")
        out.write("---\n\n")
        
        for role, doc_list in categorized.items():
            if not doc_list:
                continue
                
            out.write(f"## 🧑‍💻 Role Perspective: {role}\n\n")
            out.write(f"*This section aggregates knowledge critical for the **{role}** function.*\n\n")
            
            for doc in doc_list:
                out.write(f"### 📄 Source: `{doc['filename']}`\n")
                out.write(f"**Path:** `{doc['filepath']}`\n\n")
                
                # We will output the content, but blockquoted or inside code blocks to make it readable
                out.write(f"{doc['content']}\n\n")
                out.write("---\n\n")
                
    print(f"Master document synthesized at: {output_path}")

if __name__ == "__main__":
    root_directory = r"e:\Cores of ACE\polyglot-microservices-platform"
    json_path = os.path.join(root_directory, "scratch", "aggregated_docs.json")
    output_path = os.path.join(root_directory, "COMPREHENSIVE_MASTER_DOC.md")
    
    synthesize_master_doc(json_path, output_path)
