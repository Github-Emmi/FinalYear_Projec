"""Export the FastAPI OpenAPI schema to docs/openapi.json.

Usage (from backend/):
    python scripts/export_openapi.py

Output: backend/docs/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    # Ensure backend/ is on the Python path so `app` is importable
    backend_root = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_root))

    from app.main import create_app

    app = create_app()
    schema = app.openapi()

    output_path = backend_root / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2))

    paths_count = len(schema.get("paths", {}))
    endpoints_count = sum(len(methods) for methods in schema.get("paths", {}).values())
    schemas_count = len(schema.get("components", {}).get("schemas", {}))

    print(f"OpenAPI schema exported → {output_path}")
    print(f"  paths:     {paths_count}")
    print(f"  endpoints: {endpoints_count}")
    print(f"  schemas:   {schemas_count}")


if __name__ == "__main__":
    main()
