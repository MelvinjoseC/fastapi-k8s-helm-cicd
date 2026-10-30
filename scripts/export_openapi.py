"""Export static OpenAPI 3.1.0 schema specification from FastAPI application.
Enables client code generation, contract testing, and documentation generation in CI.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add app directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
app_dir = root_dir / "app"
sys.path.insert(0, str(app_dir))

# Mock out external env vars so app can initialize cleanly
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CACHE_ENABLED"] = "false"

from main import app


def export_schema(output_path: Path) -> None:
    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"Successfully exported OpenAPI schema to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export OpenAPI schema")
    parser.add_argument(
        "--output",
        type=Path,
        default=root_dir / "docs" / "openapi.json",
        help="Path to output openapi.json file",
    )
    args = parser.parse_args()
    export_schema(args.output)
