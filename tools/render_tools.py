"""Render the MCP tools registered by ``build_server`` as Markdown.

The built server is the source of truth for tool order, descriptions, input
schemas and output schemas. Building it with a directory also includes tools
that are conditional on having somewhere to write, such as ``document_file``.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import anyio
from mcp.types import Tool

from outrage.server import build_server
from outrage.store_sqlite import SqliteStore


def _json(value: Any) -> str:
    """Render one JSON Schema value compactly and deterministically."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _schema_type(schema: Mapping[str, Any]) -> str:
    """Render the type-bearing part of a JSON Schema for a reader."""
    if "anyOf" in schema:
        types = [_schema_type(choice) for choice in schema["anyOf"]]
        return " or ".join(dict.fromkeys(types))
    if "oneOf" in schema:
        types = [_schema_type(choice) for choice in schema["oneOf"]]
        return " or ".join(dict.fromkeys(types))
    if "enum" in schema:
        return " or ".join(_json(value) for value in schema["enum"])
    if "const" in schema:
        return _json(schema["const"])
    if schema.get("type") == "array":
        return f"array[{_schema_type(schema.get('items', {}))}]"
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1].removeprefix("_")
        return name.removesuffix("Result")
    if schema.get("type") == "object" and isinstance(schema.get("additionalProperties"), dict):
        return f"object[string, {_schema_type(schema['additionalProperties'])}]"
    kind = schema.get("type")
    if isinstance(kind, list):
        return " or ".join(kind)
    return kind or "value"


def _parameter_details(
    schema: Mapping[str, Any], *, required: bool, show_default: bool = True
) -> str:
    """Render a parameter's type, presence, default and validation bounds."""
    details = [_schema_type(schema)]
    if required:
        details.append("required")
    elif show_default and "default" in schema:
        details.append(f"default {_json(schema['default'])}")
    else:
        details.append("optional")

    constraints = (
        ("minimum", "minimum"),
        ("exclusiveMinimum", "greater than"),
        ("maximum", "maximum"),
        ("exclusiveMaximum", "less than"),
        ("minLength", "minimum length"),
        ("maxLength", "maximum length"),
        ("minItems", "minimum items"),
        ("maxItems", "maximum items"),
    )
    schemas = [schema, *schema.get("anyOf", []), *schema.get("oneOf", [])]
    for key, label in constraints:
        values = [candidate[key] for candidate in schemas if key in candidate]
        for value in dict.fromkeys(values):
            details.append(f"{label} {_json(value)}")
    return "; ".join(details)


def _append_parameters(lines: list[str], tool: Tool) -> None:
    """Append the registered input schema for one tool."""
    schema = tool.input_schema
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    lines.extend(["", "### Parameters", ""])
    if not properties:
        lines.append("None.")
        return
    for name, parameter in properties.items():
        details = _parameter_details(parameter, required=name in required)
        description = parameter.get("description", "No description.")
        lines.append(f"- `{name}` ({details}) — {description}")


def _append_return(lines: list[str], tool: Tool) -> None:
    """Append the registered output schema for one tool."""
    lines.extend(["", "### Returns", ""])
    output_schema = getattr(tool, "output_schema", None)
    if output_schema is None:
        lines.append("No output schema is registered.")
        return
    properties = output_schema.get("properties", {})
    if not properties:
        lines.append(f"`{_schema_type(output_schema)}`")
        return
    _append_schema_fields(lines, output_schema)

    for name, schema in output_schema.get("$defs", {}).items():
        display_name = name.removeprefix("_").removesuffix("Result")
        lines.extend(["", f"#### `{display_name}` fields", ""])
        _append_schema_fields(lines, schema)


def _append_schema_fields(lines: list[str], schema: Mapping[str, Any]) -> None:
    """Append the properties of one object schema as Markdown list items."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    for name, field in properties.items():
        details = _parameter_details(field, required=name in required, show_default=False)
        description = field.get("description", "No description.")
        lines.append(f"- `{name}` ({details}) — {description}")


def render(tools: Sequence[Tool]) -> str:
    """Render registered MCP ``tools`` as Markdown in server order."""
    lines = [
        "<!-- Generated by tools/render_tools.py; do not edit by hand. -->",
        "",
        "# The tools, and which one answers which question",
        "",
        "These are the tools registered by the MCP server. Their descriptions, parameters,",
        "defaults, constraints and return types come from the same server metadata sent to a",
        "client.",
    ]
    for tool in tools:
        lines.extend(["", f"## `{tool.name}`", "", (tool.description or "").strip()])
        _append_parameters(lines, tool)
        _append_return(lines, tool)
    return "\n".join(lines) + "\n"


def registered_tools() -> list[Tool]:
    """Build a complete temporary server and return its registered tools."""
    with tempfile.TemporaryDirectory() as directory:
        with SqliteStore(Path(directory)) as store:
            server = build_server(store, directory=directory)
            return anyio.run(server.list_tools)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="Markdown file to write")
    args = parser.parse_args(argv)

    try:
        args.output.write_text(render(registered_tools()), encoding="utf-8")
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
