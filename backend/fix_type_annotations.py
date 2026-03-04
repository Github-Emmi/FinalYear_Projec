#!/usr/bin/env python3
"""Remove type annotations from Column definitions in model files."""

import re
import glob
from pathlib import Path

def fix_type_annotations(file_path):
    """Remove type annotations from Column definitions."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern: variable_name: Type = Column(...) -> variable_name = Column(...)
    # This regex matches the pattern of type annotation followed by Column()
    pattern = r'(\s+)(\w+):\s*(?:str|int|bool|float|datetime|UUID|Optional\[[^\]]*\]|List\[[^\]]*\])\s*='
    replacement = r'\1\2 ='
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Fixed: {file_path}")
        return True
    return False

# Fix all model files
models_dir = Path('/Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend/app/models')
fixed_count = 0

for model_file in models_dir.glob('*.py'):
    if model_file.name.startswith('__'):
        continue
    if fix_type_annotations(model_file):
        fixed_count += 1

print(f"\nFixed {fixed_count} files")
