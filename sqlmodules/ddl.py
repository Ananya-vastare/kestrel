
import re
import ast

from database import database


SUPPORTED_TYPES = ["INTEGER", "TEXT", "REAL"]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def split_definitions(definitions):
    """
    Split column definitions using commas.
    Ignore commas inside parentheses and quoted strings.
    """

    result = []
    current = []
    depth = 0
    quote = None
    i = 0

    while i < len(definitions):
        char = definitions[i]

        if quote:
            current.append(char)

            # Handle escaped SQL quotes, e.g. 'Ananya''s'
            if char == quote:
                if i + 1 < len(definitions) and definitions[i + 1] == quote:
                    current.append(definitions[i + 1])
                    i += 1
                else:
                    quote = None

        elif char in ("'", '"'):
            quote = char
            current.append(char)

        elif char == "(":
            depth += 1
            current.append(char)

        elif char == ")":
            depth -= 1

            if depth < 0:
                raise ValueError("Unmatched closing parenthesis")

            current.append(char)

        elif char == "," and depth == 0:
            item = "".join(current).strip()

            if not item:
                raise ValueError("Empty column definition")

            result.append(item)
            current = []

        else:
            current.append(char)

        i += 1

    if quote:
        raise ValueError("Unclosed quoted string")

    if depth != 0:
        raise ValueError("Unclosed parentheses")

    final_item = "".join(current).strip()

    if final_item:
        result.append(final_item)

    return result


def extract_parenthesized(text, start):
    """
    Extract content inside balanced parentheses.
    Supports nested parentheses and quoted strings.
    """

    if start >= len(text) or text[start] != "(":
        raise ValueError("Expected opening parenthesis")

    depth = 0
    quote = None
    i = start

    while i < len(text):
        char = text[i]

        if quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 1
                else:
                    quote = None

        elif char in ("'", '"'):
            quote = char

        elif char == "(":
            depth += 1

        elif char == ")":
            depth -= 1

            if depth == 0:
                return text[start + 1:i], i + 1

        i += 1

    raise ValueError("Unclosed parentheses")


def parse_default(value):
    """
    Parse SQL DEFAULT values.
    Supports strings, integers, decimals and NULL.
    """

    value = value.strip()

    if value.upper() == "NULL":
        return None

    # SQL single-quoted string
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")

    # Double-quoted string
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('""', '"')

    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid DEFAULT value: {value}")


# ============================================================
# CREATE TABLE PARSER
# ============================================================

def parse_create_table(definitions):

    columns = {}

    constraints = {
        "primary_key": [],
        "unique": [],
        "not_null": [],
        "foreign_keys": [],
        "defaults": {},
        "checks": [],
        "auto_increment": []
    }

    for definition in split_definitions(definitions):

        definition = definition.strip()

        if not definition:
            continue

        # ----------------------------------------------------
        # TABLE-LEVEL PRIMARY KEY
        # ----------------------------------------------------

        match = re.fullmatch(
            r"PRIMARY\s+KEY\s*\((.*?)\)",
            definition,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            if constraints["primary_key"]:
                raise ValueError("Multiple PRIMARY KEY constraints")

            constraints["primary_key"] = [
                col.strip() for col in match.group(1).split(",")
            ]

            continue

        # ----------------------------------------------------
        # TABLE-LEVEL UNIQUE
        # ----------------------------------------------------

        match = re.fullmatch(
            r"UNIQUE\s*\((.*?)\)",
            definition,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            group = [
                col.strip() for col in match.group(1).split(",")
            ]

            constraints["unique"].append(group)
            continue

        # ----------------------------------------------------
        # TABLE-LEVEL FOREIGN KEY
        # ----------------------------------------------------

        match = re.fullmatch(
            r"FOREIGN\s+KEY\s*\((.*?)\)\s*"
            r"REFERENCES\s+(\w+)\s*\((.*?)\)",
            definition,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            local_columns = [
                col.strip() for col in match.group(1).split(",")
            ]

            referenced_table = match.group(2)

            referenced_columns = [
                col.strip() for col in match.group(3).split(",")
            ]

            if len(local_columns) != len(referenced_columns):
                raise ValueError("Foreign key column count mismatch")

            constraints["foreign_keys"].append({
                "columns": local_columns,
                "referenced_table": referenced_table,
                "referenced_columns": referenced_columns
            })

            continue

        # ----------------------------------------------------
        # COLUMN DEFINITION
        # ----------------------------------------------------

        match = re.match(
            r"^(\w+)\s+(INTEGER|TEXT|REAL)\b(.*)$",
            definition,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            raise ValueError(
                f"Invalid column definition: {definition}"
            )

        column_name, data_type, remaining = match.groups()

        if column_name in columns:
            raise ValueError(
                f"Duplicate column '{column_name}'"
            )

        data_type = data_type.upper()

        columns[column_name] = data_type

        remaining = remaining.strip()

        # ----------------------------------------------------
        # PRIMARY KEY
        # ----------------------------------------------------

        if re.search(
            r"\bPRIMARY\s+KEY\b",
            remaining,
            re.IGNORECASE
        ):

            if constraints["primary_key"]:
                raise ValueError("Multiple PRIMARY KEY constraints")

            constraints["primary_key"] = [column_name]

            if column_name not in constraints["not_null"]:
                constraints["not_null"].append(column_name)

        # ----------------------------------------------------
        # UNIQUE
        # ----------------------------------------------------

        if re.search(
            r"\bUNIQUE\b",
            remaining,
            re.IGNORECASE
        ):

            constraints["unique"].append([column_name])

        # ----------------------------------------------------
        # NOT NULL
        # ----------------------------------------------------

        if re.search(
            r"\bNOT\s+NULL\b",
            remaining,
            re.IGNORECASE
        ):

            if column_name not in constraints["not_null"]:
                constraints["not_null"].append(column_name)

        # ----------------------------------------------------
        # AUTO_INCREMENT
        # ----------------------------------------------------

        if re.search(
            r"\bAUTO_INCREMENT\b|\bAUTOINCREMENT\b",
            remaining,
            re.IGNORECASE
        ):

            if data_type != "INTEGER":
                raise ValueError(
                    "AUTO_INCREMENT requires INTEGER"
                )

            constraints["auto_increment"].append(column_name)

        # ----------------------------------------------------
        # DEFAULT
        # ----------------------------------------------------

        default_match = re.search(
            r"\bDEFAULT\s+"
            r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[^\s,]+)",
            remaining,
            re.IGNORECASE
        )

        if default_match:

            constraints["defaults"][column_name] = parse_default(
                default_match.group(1)
            )

        # ----------------------------------------------------
        # CHECK
        # ----------------------------------------------------

        check_match = re.search(
            r"\bCHECK\s*\(",
            remaining,
            re.IGNORECASE
        )

        if check_match:

            opening = remaining.find(
                "(",
                check_match.start()
            )

            expression, _ = extract_parenthesized(
                remaining,
                opening
            )

            constraints["checks"].append({
                "column": column_name,
                "expression": expression.strip()
            })

        # ----------------------------------------------------
        # COLUMN-LEVEL FOREIGN KEY
        # ----------------------------------------------------

        reference_match = re.search(
            r"\bREFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
            remaining,
            re.IGNORECASE
        )

        if reference_match:

            constraints["foreign_keys"].append({
                "columns": [column_name],
                "referenced_table": reference_match.group(1),
                "referenced_columns": [reference_match.group(2)]
            })

    # ========================================================
    # VALIDATE CONSTRAINTS
    # ========================================================

    if not columns:
        raise ValueError("Table must have at least one column")

    # Validate primary key
    for column in constraints["primary_key"]:

        if column not in columns:
            raise ValueError(
                f"Unknown PRIMARY KEY column '{column}'"
            )

    # Validate unique columns
    for group in constraints["unique"]:

        for column in group:

            if column not in columns:
                raise ValueError(
                    f"Unknown UNIQUE column '{column}'"
                )

    # Validate NOT NULL columns
    for column in constraints["not_null"]:

        if column not in columns:
            raise ValueError(
                f"Unknown NOT NULL column '{column}'"
            )

    # Validate foreign key columns
    for foreign_key in constraints["foreign_keys"]:

        for column in foreign_key["columns"]:

            if column not in columns:
                raise ValueError(
                    f"Unknown FOREIGN KEY column '{column}'"
                )

    # Validate DEFAULT columns
    for column in constraints["defaults"]:

        if column not in columns:
            raise ValueError(
                f"Unknown DEFAULT column '{column}'"
            )

    # Validate AUTO_INCREMENT
    if len(constraints["auto_increment"]) > 1:
        raise ValueError(
            "Only one AUTO_INCREMENT column is supported"
        )

    for column in constraints["auto_increment"]:

        if column not in constraints["primary_key"]:
            raise ValueError(
                "AUTO_INCREMENT must be a PRIMARY KEY"
            )

    return columns, constraints


# ============================================================
# DDL COMMAND HANDLER
# ============================================================

def ddl_command(command):

    command = command.strip()

    # Remove optional trailing semicolon
    if command.endswith(";"):
        command = command[:-1].strip()

    # ========================================================
    # CREATE TABLE
    # ========================================================

    create_match = re.match(
        r"^CREATE\s+TABLE\s+(\w+)\s*\(",
        command,
        re.IGNORECASE
    )

    if create_match:

        table_name = create_match.group(1)

        if table_name in database:
            return f"ERROR: Table '{table_name}' already exists"

        opening = command.find(
            "(",
            create_match.start()
        )

        try:

            definitions, end_position = extract_parenthesized(
                command,
                opening
            )

            # Reject unexpected text after closing parenthesis
            if command[end_position:].strip():
                return "ERROR: Unexpected text after CREATE TABLE definition"

            columns, constraints = parse_create_table(definitions)

            database[table_name] = {
                "columns": columns,
                "constraints": constraints,
                "rows": []
            }

            return f"Table '{table_name}' created successfully"

        except ValueError as error:

            return f"ERROR: {error}"

    # ========================================================
    # ALTER TABLE ADD COLUMN
    # ========================================================

    match = re.fullmatch(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+"
        r"(\w+)\s+(INTEGER|TEXT|REAL)",
        command,
        re.IGNORECASE
    )

    if match:

        table_name, column_name, data_type = match.groups()

        data_type = data_type.upper()

        if table_name not in database:
            return f"ERROR: Table '{table_name}' does not exist"

        table = database[table_name]

        if column_name in table["columns"]:
            return f"ERROR: Column '{column_name}' already exists"

        if data_type not in SUPPORTED_TYPES:
            return f"ERROR: Unsupported data type '{data_type}'"

        table["columns"][column_name] = data_type

        for row in table["rows"]:
            row[column_name] = None

        return f"Column '{column_name}' added successfully"

    # ========================================================
    # TRUNCATE TABLE
    # ========================================================

    match = re.fullmatch(
        r"TRUNCATE\s+TABLE\s+(\w+)",
        command,
        re.IGNORECASE
    )

    if match:

        table_name = match.group(1)

        if table_name not in database:
            return f"ERROR: Table '{table_name}' does not exist"

        database[table_name]["rows"].clear()

        return f"Table '{table_name}' truncated successfully"

    # ========================================================
    # DROP TABLE
    # ========================================================

    match = re.fullmatch(
        r"DROP\s+TABLE\s+(\w+)",
        command,
        re.IGNORECASE
    )

    if match:

        table_name = match.group(1)

        if table_name not in database:
            return f"ERROR: Table '{table_name}' does not exist"

        del database[table_name]

        return f"Table '{table_name}' dropped successfully"

    return "ERROR: Unsupported DDL command"
