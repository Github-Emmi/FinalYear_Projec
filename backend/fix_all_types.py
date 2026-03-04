#!/usr/bin/env python3
"""Fix all SQLAlchemy type issues comprehensively."""

import re
from pathlib import Path

def fix_all_types(file_path):
    """Fix all type references in Column definitions."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Replace all Python types with SQLAlchemy types
    replacements = [
        (r'Column\(\s*int\s*,', 'Column(Integer,'),
        (r'Column\(\s*bool\s*,', 'Column(Boolean,'),
        (r'Column\(\s*float\s*,', 'Column(Float,'),
        (r'Column\(\s*str\s*,', 'Column(String,'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Check if Integer, Float are imported
    if re.search(r'Column\((Integer|Float)', content):
        if 'from sqlalchemy import' in content:
            # Check the import line
            if 'Integer' not in content.split('from sqlalchemy import')[1].split('\n')[0]:
                # Need to add Integer to imports
                content = content.replace(
                    'from sqlalchemy import',
                    'from sqlalchemy import Integer, Float,'
                ).replace(
                    'from sqlalchemy import Integer, Float,from sqlalchemy import',
                    'from sqlalchemy import Integer, Float,'
                )
    
    if original_content != content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed: {file_path}")
        return True
    return False

# Fix all model files
models_dir = Path('/Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend/app/models')
fixed_count = 0

for model_file in sorted(models_dir.glob('*.py')):
    if model_file.name.startswith('__'):
        continue
    if fix_all_types(model_file):
        fixed_count += 1

print(f"\nFixed {fixed_count} files")
