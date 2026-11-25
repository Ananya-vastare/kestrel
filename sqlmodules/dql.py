
import re

from database import database
from sqlmodules.conditions import evaluate_condition
from sqlmodules.aggregate import aggregate_function


def dql_command(command):

    command = command.strip().rstrip(";")

    pattern = (
        r"SELECT\s+(.+?)\s+FROM\s+(\w+)"
        r"(?:\s+WHERE\s+(.+?))?"
        r"(?:\s+GROUP\s+BY\s+(\w+))?"
        r"(?:\s+HAVING\s+(.+?))?"
        r"(?:\s+ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?)?"
        r"(?:\s+LIMIT\s+(\d+))?"
    )

    match = re.fullmatch(pattern, command, re.IGNORECASE)

    if not match:
        return "ERROR: Invalid SELECT syntax"

    selected, table_name, where_clause, group_column, having_clause, order_column, order_direction, limit = match.groups()

    if table_name not in database:
        return f"ERROR: Table '{table_name}' does not exist"

    table = database[table_name]
    schema = table["columns"]
    rows = list(table["rows"])

    # WHERE
    if where_clause:
        try:
            rows = [
                row for row in rows
                if evaluate_condition(row, where_clause)
            ]
        except (ValueError, TypeError, KeyError) as error:
            return f"ERROR: {error}"

    # GROUP BY
    if group_column:

        if group_column not in schema:
            return f"ERROR: Unknown column '{group_column}'"

        groups = {}

        for row in rows:
            key = row[group_column]
            groups.setdefault(key, []).append(row)

        aggregate_matches = re.findall(
            r"(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*(\*|\w+)\s*\)",
            selected,
            re.IGNORECASE
        )

        result_rows = []

        for key, group_rows in groups.items():

            result = {group_column: key}

            for function, column in aggregate_matches:
                aggregate_name = f"{function.upper()}({column})"

                result[aggregate_name] = aggregate_function(
                    function, group_rows, column
                )

            result_rows.append(result)

        rows = result_rows

        # HAVING
        if having_clause:
            try:
                rows = [
                    row for row in rows
                    if evaluate_condition(row, having_clause)
                ]
            except (ValueError, TypeError, KeyError) as error:
                return f"ERROR: {error}"

        columns = [group_column]

        for function, column in aggregate_matches:
            columns.append(f"{function.upper()}({column})")

    else:

        if having_clause:
            return "ERROR: HAVING requires GROUP BY"

        aggregate_match = re.fullmatch(
            r"(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*(\*|\w+)\s*\)",
            selected,
            re.IGNORECASE
        )

        if aggregate_match:
            function, column = aggregate_match.groups()

            try:
                value = aggregate_function(function, rows, column)
                return f"{function.upper()}({column})\n{value}"
            except (ValueError, TypeError, KeyError) as error:
                return f"ERROR: {error}"

        if selected == "*":
            columns = list(schema.keys())
        else:
            columns = [col.strip() for col in selected.split(",")]

        for col in columns:
            if col not in schema:
                return f"ERROR: Unknown column '{col}'"

    # ORDER BY
    if order_column:

        if order_column not in columns:
            return f"ERROR: Unknown ORDER BY column '{order_column}'"

        rows.sort(
            key=lambda row: row[order_column],
            reverse=(order_direction or "ASC").upper() == "DESC"
        )

    # LIMIT
    if limit:
        rows = rows[:int(limit)]

    if not rows:
        return "Empty set"

    # Display output
    widths = {
        col: max(
            len(col),
            max(len(str(row.get(col, "NULL"))) for row in rows)
        )
        for col in columns
    }

    output = []

    output.append(
        " | ".join(col.ljust(widths[col]) for col in columns)
    )

    output.append(
        "-+-".join("-" * widths[col] for col in columns)
    )

    for row in rows:
        output.append(
            " | ".join(
                str(row.get(col, "NULL")).ljust(widths[col])
                for col in columns
            )
        )

    output.append(f"{len(rows)} row(s) returned")

    return "\n".join(output)
