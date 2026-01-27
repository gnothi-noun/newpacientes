#!/usr/bin/env python3
"""
Efficient MySQL dump to JSON converter.
Streams the file line-by-line to handle large dumps without loading everything into memory.
"""

import json
import re
import sys
from pathlib import Path
from typing import Generator


def parse_create_table(line: str, file) -> tuple[str, list[str]]:
    """Parse CREATE TABLE statement to extract table name and columns."""
    match = re.search(r'CREATE TABLE `(\w+)`', line)
    if not match:
        return None, []

    table_name = match.group(1)
    columns = []

    for table_line in file:
        table_line = table_line.strip()
        if table_line.startswith(')'):
            break
        # Match column definitions like `column_name` type
        col_match = re.match(r'`(\w+)`\s+', table_line)
        if col_match:
            columns.append(col_match.group(1))

    return table_name, columns


def parse_values(values_str: str) -> list:
    """Parse a VALUES clause, handling quoted strings with commas and escaped quotes."""
    values = []
    current = ''
    in_string = False
    escape_next = False

    i = 0
    while i < len(values_str):
        char = values_str[i]

        if escape_next:
            current += char
            escape_next = False
        elif char == '\\':
            current += char
            escape_next = True
        elif char == "'" and not in_string:
            in_string = True
            current += char
        elif char == "'" and in_string:
            # Check for escaped quote ''
            if i + 1 < len(values_str) and values_str[i + 1] == "'":
                current += "''"
                i += 1
            else:
                in_string = False
                current += char
        elif char == ',' and not in_string:
            values.append(parse_value(current.strip()))
            current = ''
        else:
            current += char
        i += 1

    if current.strip():
        values.append(parse_value(current.strip()))

    return values


def parse_value(val: str):
    """Convert a SQL value to Python type."""
    if val == 'NULL':
        return None
    if val.startswith("'") and val.endswith("'"):
        # Remove quotes and unescape
        return val[1:-1].replace("\\'", "'").replace("''", "'").replace("\\\\", "\\")
    try:
        if '.' in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def extract_insert_data(line: str, columns: list[str]) -> Generator[dict, None, None]:
    """Extract rows from an INSERT statement."""
    # Match: INSERT INTO `table` (...) VALUES (...),(...);
    # We need to handle multi-row inserts

    # Find VALUES keyword
    values_start = line.find('VALUES ')
    if values_start == -1:
        return

    values_part = line[values_start + 7:].rstrip(';\n')

    # Split by ),( but be careful about strings containing these patterns
    depth = 0
    in_string = False
    escape_next = False
    current_row = ''

    for i, char in enumerate(values_part):
        if escape_next:
            current_row += char
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            current_row += char
            continue

        if char == "'" and not escape_next:
            in_string = not in_string
            current_row += char
            continue

        if not in_string:
            if char == '(':
                if depth == 0:
                    current_row = ''
                else:
                    current_row += char
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    values = parse_values(current_row)
                    if len(values) == len(columns):
                        yield dict(zip(columns, values))
                else:
                    current_row += char
            else:
                if depth > 0:
                    current_row += char
        else:
            current_row += char


def parse_mysql_dump(filepath: str, verbose: bool = False) -> dict:
    """
    Parse MySQL dump file and return dict with all tables.

    Args:
        filepath: Path to the .sql dump file
        verbose: If True, print progress to stderr

    Returns:
        dict with table names as keys and lists of row dicts as values
        Example: {"users": [{"id": 1, "name": "John"}, ...], "orders": [...]}
    """
    database = {}
    current_table = None
    current_columns = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line_stripped = line.strip()

            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('--') or line_stripped.startswith('/*'):
                continue

            # Parse CREATE TABLE
            if line_stripped.startswith('CREATE TABLE'):
                current_table, current_columns = parse_create_table(line, f)
                if current_table:
                    database[current_table] = []
                    if verbose:
                        print(f"Found table: {current_table} with {len(current_columns)} columns", file=sys.stderr)

            # Parse INSERT statements
            elif line_stripped.startswith('INSERT INTO'):
                # Extract table name from INSERT
                match = re.search(r'INSERT INTO `(\w+)`', line_stripped)
                if match:
                    table_name = match.group(1)
                    if table_name in database:
                        for row in extract_insert_data(line, current_columns):
                            database[table_name].append(row)

    return database


def convert_dump_to_json(
    sql_path: str,
    json_path: str | None = None,
    indent: int = 2,
    verbose: bool = False
) -> dict:
    """
    Convert a MySQL dump file to JSON.

    Args:
        sql_path: Path to the .sql dump file
        json_path: Output path for JSON (default: same name with .json extension)
        indent: JSON indentation (default: 2, use None for compact)
        verbose: If True, print progress

    Returns:
        The parsed database dict

    Example:
        from parse_mysql_dump import convert_dump_to_json

        # Convert and save to JSON
        data = convert_dump_to_json("backup.sql", "output.json")

        # Just parse without saving
        data = parse_mysql_dump("backup.sql")
    """
    sql_path = Path(sql_path)

    if json_path is None:
        json_path = sql_path.with_suffix('.json')

    if verbose:
        print(f"Parsing: {sql_path}", file=sys.stderr)

    database = parse_mysql_dump(str(sql_path), verbose=verbose)

    if verbose:
        print("\nSummary:", file=sys.stderr)
        for table, rows in database.items():
            print(f"  {table}: {len(rows)} rows", file=sys.stderr)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(database, f, indent=indent, ensure_ascii=False, default=str)

    if verbose:
        print(f"\nOutput written to: {json_path}", file=sys.stderr)

    return database


def main():
    if len(sys.argv) < 2:
        dump_file = Path(__file__).parent / "RA.sql"
    else:
        dump_file = Path(sys.argv[1])

    if not dump_file.exists():
        print(f"Error: File not found: {dump_file}", file=sys.stderr)
        sys.exit(1)

    convert_dump_to_json(str(dump_file), verbose=True)


if __name__ == '__main__':
    main()
