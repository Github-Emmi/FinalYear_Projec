#!/usr/bin/env python3
"""Fix SQLAlchemy type issues in model files."""

import re
from pathlib import Path

def fix_sqlalchemy_types(file_path):
    """Fix SQLAlchemy type references."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix: Column(bool, ...) -> Column(Boolean, ...)
    # But be careful not to change boolean in comments/strings outside Column()
    original_content = content
    
    # Replace Column(bool, ...) with Column(Boolean, ...)
    content = re.sub(r'Column\(bool,', 'Column(Boolean,', content)
    
    # Also fix cases like Column( bool, ...)
    content = re.sub(r'Column\(\s*bool\s*,', 'Column(Boolean,', content)
    
    # Make sure Boolean is imported
    if "Column(Boolean," in content and "from sqlalchemy import" in content:
        # Check if Boolean is already imported
        if "Boolean" not in content.split('\n')[0:20]:  # Check first 20 lines for imports
            # Add Boolean to imports
            import_line = None
            for i, line in enumerate(content.split('\n')):
                if 'from sqlalchemy import' in line and 'Boolean' not in line:
                    # Find the line and add Boolean
                    if line.strip().endswith(','):
                        # Multi-line import
                        pass
                    else:
                        # Single line import, add Boolean if not present
                        pass
                    break
    
    if original_content != content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed: {file_path}")
        return True
    return False

# Fix all model files
models_dir = Path('/Volumes/EmmiDev256G/Projects/Backup/FinalYear_Projec/backend/app/models')
fixed_count = 0

for model_file in models_dir.glob('*.py'):
    if model_file.name.startswith('__'):
        continue
    if fix_sqlalchemy_types(model_file):
        fixed_count += 1

print(f"\nFixed {fixed_count} files")
