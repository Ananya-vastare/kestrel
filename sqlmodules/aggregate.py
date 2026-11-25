
def aggregate_function(function, rows, column=None):

    function = function.upper()

    if function == "COUNT":
        if column == "*":
            return len(rows)

        return sum(
            1 for row in rows
            if row.get(column) is not None
        )

    if column not in rows[0] if rows else column is not None:
        raise ValueError(f"Unknown column: {column}")

    values = [
        row[column]
        for row in rows
        if row.get(column) is not None
    ]

    if not values:
        return None

    if function == "SUM":
        return sum(values)

    elif function == "AVG":
        return sum(values) / len(values)

    elif function == "MIN":
        return min(values)

    elif function == "MAX":
        return max(values)

    else:
        raise ValueError(f"Unsupported aggregate function: {function}")
