# references_finder.py
import os
from pathlib import Path

def find_references():
    references = []
    search_patterns = [
        'workflow.models.Staff', 
        'workflow.Staff',
        'from workflow.views import staff_',
        'url staff/',
        'api/staff/'
    ]
    
    root_dir = Path('.')
    
    for file_path in root_dir.glob('**/*'):
        # Skip directories, virtual environments, and compiled files
        if (file_path.is_dir() or 
            '.venv' in str(file_path) or 
            '.git' in str(file_path) or
            '__pycache__' in str(file_path) or
            not file_path.suffix.lower() in ['.py', '.html', '.js']):
            continue
            
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1']:
                try:
                    content = file_path.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            # Check if any pattern is in the content
            for pattern in search_patterns:
                if pattern in content:
                    references.append((str(file_path), pattern))
                    break
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return references

results = find_references()

# Group by file for better readability
files_dict = {}
for file_path, pattern in results:
    if file_path not in files_dict:
        files_dict[file_path] = []
    files_dict[file_path].append(pattern)

# Print results
print(f"Found {len(results)} references in {len(files_dict)} files:")
for file_path, patterns in files_dict.items():
    print(f"\n{file_path}:")
    for pattern in patterns:
        print(f"  - {pattern}")
            