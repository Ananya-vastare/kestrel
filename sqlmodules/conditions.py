
import re


def evaluate_condition(row, condition):

    condition = condition.strip()

    parts = re.split(
        r"\s+(AND|OR)\s+",
        condition,
        flags=re.IGNORECASE
    )

    results = []

    for part in parts:

        part = part.strip()

        if part.upper() in ["AND", "OR"]:
            continue

        match = re.fullmatch(
            r"((?:COUNT|SUM|AVG|MIN|MAX)\s*\(\s*(?:\*|\w+)\s*\)|\w+)\s*(>=|<=|!=|<>|=|>|<)\s*(.+)",
            part,
            re.IGNORECASE
        )

        if not match:
            raise ValueError(f"Invalid condition: {part}")

        column, operator, value = match.groups()

        # Normalise aggregate column names
        if "(" in column:
            column = re.sub(r"\s+", "", column).upper()

        if column not in row:
            raise ValueError(f"Unknown column: {column}")

        value = value.strip().strip("'\"")
        actual = row[column]

        # Convert comparison value to the actual value's type
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            try:
                value = float(value) if "." in value else int(value)
            except ValueError:
                raise ValueError(f"Invalid numeric value: {value}")

        if operator == "=":
            result = actual == value
        elif operator in ["!=", "<>"]:
            result = actual != value
        elif operator == ">":
            result = actual > value
        elif operator == "<":
            result = actual < value
        elif operator == ">=":
            result = actual >= value
        elif operator == "<=":
            result = actual <= value

        results.append(result)

    if not results:
        raise ValueError("Empty condition")

    final_result = results[0]
    result_index = 1

    for part in parts:

        if part.upper() == "AND":
            final_result = final_result and results[result_index]
            result_index += 1

        elif part.upper() == "OR":
            final_result = final_result or results[result_index]
            result_index += 1

    return final_result
