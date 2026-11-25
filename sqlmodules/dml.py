
import re
import ast

from database import database
from sqlmodules.conditions import evaluate_condition
from sqlmodules.ddl import split_definitions

from sqlmodules.constraints import (
    validate_row,
    validate_delete,
    validate_referenced_update
)


# --------------------------------------------------
# SQL VALUE PARSER
# --------------------------------------------------

def parse_sql_value(value):

    value = value.strip()

    if value.upper() == "DEFAULT":
        return "DEFAULT"

    if value.upper() == "NULL":
        return None

    try:
        return ast.literal_eval(value)

    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid SQL value: {value}")


# --------------------------------------------------
# INSERT ROW PREPARATION
# --------------------------------------------------

def prepare_insert_row(table, supplied_columns, supplied_values):

    columns = table["columns"]
    constraints = table.get("constraints", {})

    missing = object()

    row = {
        column: missing
        for column in columns
    }

    # Assign supplied values
    for column, value in zip(supplied_columns, supplied_values):

        if column not in columns:
            raise ValueError(f"Unknown column '{column}'")

        if value != "DEFAULT":
            row[column] = value

    # Apply DEFAULT and AUTO_INCREMENT
    sequences = table.setdefault("sequences", {})

    for column in columns:

        if row[column] is not missing:
            continue

        if column in constraints.get("auto_increment", []):

            existing_values = [
                existing[column]
                for existing in table["rows"]
                if existing.get(column) is not None
            ]

            next_value = max(
                sequences.get(column, 1),
                max(existing_values, default=0) + 1
            )

            row[column] = next_value
            sequences[column] = next_value + 1

        elif column in constraints.get("defaults", {}):

            row[column] = constraints["defaults"][column]

        else:
            row[column] = None

    # Update AUTO_INCREMENT sequence when explicit IDs are supplied
    for column in constraints.get("auto_increment", []):

        value = row[column]

        if value is not None:

            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(
                    f"AUTO_INCREMENT column '{column}' requires INTEGER"
                )

            sequences[column] = max(
                sequences.get(column, 1),
                value + 1
            )

    return row


# --------------------------------------------------
# INSERT COMMAND
# --------------------------------------------------

def insert_command(command):

    match = re.fullmatch(
        r"INSERT\s+INTO\s+(\w+)\s*"
        r"(?:\((.*?)\))?\s*"
        r"VALUES\s*\((.*)\)",
        command,
        re.IGNORECASE
    )

    if not match:
        return "ERROR: Invalid INSERT syntax"

    table_name, column_part, values_part = match.groups()

    if table_name not in database:
        return f"ERROR: Table '{table_name}' does not exist"

    table = database[table_name]

    try:

        table_columns = list(table["columns"].keys())

        # Determine supplied columns
        if column_part:

            supplied_columns = [
                column.strip()
                for column in split_definitions(column_part)
            ]

        else:
            supplied_columns = table_columns

        # Duplicate column check
        if len(supplied_columns) != len(set(supplied_columns)):
            raise ValueError("Duplicate INSERT column")

        # Parse supplied values
        supplied_values = [
            parse_sql_value(value)
            for value in split_definitions(values_part)
        ]

        if len(supplied_columns) != len(supplied_values):
            raise ValueError("Column count mismatch")

        for column in supplied_columns:

            if column not in table["columns"]:
                raise ValueError(f"Unknown column '{column}'")

        # Construct complete row
        row = prepare_insert_row(
            table,
            supplied_columns,
            supplied_values
        )

        # Validate every constraint
        validate_row(table_name, row)

        # Insert only after validation succeeds
        table["rows"].append(row)

        return "1 row inserted successfully"

    except (
        ValueError,
        SyntaxError,
        TypeError,
        KeyError,
        ZeroDivisionError
    ) as error:

        return f"ERROR: {error}"


# --------------------------------------------------
# UPDATE COMMAND
# --------------------------------------------------

def update_command(command):

    match = re.fullmatch(
        r"UPDATE\s+(\w+)\s+SET\s+(.+?)"
        r"(?:\s+WHERE\s+(.+))?",
        command,
        re.IGNORECASE
    )

    if not match:
        return "ERROR: Invalid UPDATE syntax"

    table_name, assignments_part, where_clause = match.groups()

    if table_name not in database:
        return f"ERROR: Table '{table_name}' does not exist"

    table = database[table_name]

    try:

        assignments = {}

        # Parse multiple assignments
        for assignment in split_definitions(assignments_part):

            assignment_match = re.fullmatch(
                r"(\w+)\s*=\s*(.+)",
                assignment,
                re.IGNORECASE
            )

            if not assignment_match:
                raise ValueError(
                    f"Invalid assignment: {assignment}"
                )

            column, value = assignment_match.groups()

            if column not in table["columns"]:
                raise ValueError(f"Unknown column '{column}'")

            if column in assignments:
                raise ValueError(f"Duplicate assignment for '{column}'")

            assignments[column] = parse_sql_value(value)

        if not assignments:
            raise ValueError("No columns specified for UPDATE")

        # Prepare all changes before modifying the table.
        proposed_rows = [
            row.copy()
            for row in table["rows"]
        ]

        updated_count = 0

        for index, old_row in enumerate(table["rows"]):

            if where_clause:

                if not evaluate_condition(old_row, where_clause):
                    continue

            new_row = old_row.copy()

            # Apply all requested assignments
            for column, value in assignments.items():

                if value == "DEFAULT":
                    value = table.get(
                        "constraints", {}
                    ).get("defaults", {}).get(column)

                new_row[column] = value

            # Validate constraints against the complete proposed table.
            validate_row(
                table_name,
                new_row,
                ignore_row=old_row,
                rows=proposed_rows
            )

            # Protect parent keys referenced by child tables.
            validate_referenced_update(
                table_name,
                old_row,
                new_row
            )

            proposed_rows[index] = new_row

            updated_count += 1

        # Commit changes only after all selected rows pass validation.
        table["rows"] = proposed_rows

        return f"{updated_count} row(s) updated successfully"

    except (
        ValueError,
        SyntaxError,
        TypeError,
        KeyError,
        ZeroDivisionError
    ) as error:

        return f"ERROR: {error}"


# --------------------------------------------------
# DELETE COMMAND
# --------------------------------------------------

def delete_command(command):

    match = re.fullmatch(
        r"DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?",
        command,
        re.IGNORECASE
    )

    if not match:
        return "ERROR: Invalid DELETE syntax"

    table_name, where_clause = match.groups()

    if table_name not in database:
        return f"ERROR: Table '{table_name}' does not exist"

    table = database[table_name]

    try:

        rows = table["rows"]

        # Identify rows to delete
        if where_clause:

            rows_to_delete = [
                row for row in rows
                if evaluate_condition(row, where_clause)
            ]

        else:

            rows_to_delete = list(rows)

        # Validate all foreign-key references before deleting
        for row in rows_to_delete:

            validate_delete(
                table_name,
                row
            )

        # Delete only after all validations succeed
        deleted_ids = {
            id(row)
            for row in rows_to_delete
        }

        table["rows"] = [
            row for row in rows
            if id(row) not in deleted_ids
        ]

        return (
            f"{len(rows_to_delete)} row(s) deleted successfully"
        )

    except (
        ValueError,
        SyntaxError,
        TypeError,
        KeyError
    ) as error:

        return f"ERROR: {error}"


# --------------------------------------------------
# MAIN DML COMMAND ROUTER
# --------------------------------------------------

def dml_command(command):

    command = command.strip().rstrip(";").strip()

    if not command:
        return "ERROR: Empty DML command"

    operation = command.split()[0].upper()

    if operation == "INSERT":
        return insert_command(command)

    elif operation == "UPDATE":
        return update_command(command)

    elif operation == "DELETE":
        return delete_command(command)

    return "ERROR: Unsupported DML command"
