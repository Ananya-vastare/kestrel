
import ast
import operator


# Supported operations for CHECK expressions
BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod
}

COMPARISON_OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le
}


def evaluate_check_expression(expression, row):

    tree = ast.parse(expression, mode="eval")

    def evaluate(node):

        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id not in row:
                raise ValueError(f"Unknown CHECK column '{node.id}'")
            return row[node.id]

        if isinstance(node, ast.BinOp):
            operation = BINARY_OPERATORS.get(type(node.op))

            if operation is None:
                raise ValueError("Unsupported CHECK operation")

            return operation(
                evaluate(node.left),
                evaluate(node.right)
            )

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -evaluate(node.operand)

            if isinstance(node.op, ast.UAdd):
                return evaluate(node.operand)

            if isinstance(node.op, ast.Not):
                return not evaluate(node.operand)

        if isinstance(node, ast.BoolOp):
            values = [evaluate(value) for value in node.values]

            if isinstance(node.op, ast.And):
                return all(values)

            if isinstance(node.op, ast.Or):
                return any(values)

        if isinstance(node, ast.Compare):
            left = evaluate(node.left)

            for operation_node, comparator in zip(
                node.ops, node.comparators
            ):
                right = evaluate(comparator)

                operation = COMPARISON_OPERATORS.get(
                    type(operation_node)
                )

                if operation is None:
                    raise ValueError("Unsupported CHECK comparison")

                if left is None or right is None:
                    return True

                if not operation(left, right):
                    return False

                left = right

            return True

        raise ValueError("Invalid CHECK expression")

    return evaluate(tree)


def validate_data_type(column, value, data_type):

    if value is None:
        return

    if data_type == "INTEGER":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(
                f"Invalid INTEGER value for '{column}'"
            )

    elif data_type == "REAL":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(
                f"Invalid REAL value for '{column}'"
            )

    elif data_type == "TEXT":
        if not isinstance(value, str):
            raise ValueError(
                f"Invalid TEXT value for '{column}'"
            )


def validate_row(table_name, row, ignore_row=None, rows=None):

    if table_name not in database:
        raise ValueError(f"Table '{table_name}' does not exist")

    table = database[table_name]
    columns = table["columns"]
    constraints = table.get("constraints", {})

    if rows is None:
        rows = table["rows"]

    # ---------------- DATA TYPES ----------------

    for column, data_type in columns.items():
        validate_data_type(
            column,
            row.get(column),
            data_type
        )

    # ---------------- NOT NULL ----------------

    not_null_columns = set(
        constraints.get("not_null", [])
    )

    not_null_columns.update(
        constraints.get("primary_key", [])
    )

    for column in not_null_columns:
        if row.get(column) is None:
            raise ValueError(
                f"Column '{column}' cannot be NULL"
            )

    # ---------------- PRIMARY KEY ----------------

    primary_key = constraints.get("primary_key", [])

    if primary_key:
        for existing in rows:

            if existing is ignore_row:
                continue

            if all(
                existing.get(column) == row.get(column)
                for column in primary_key
            ):
                raise ValueError("Duplicate PRIMARY KEY value")

    # ---------------- UNIQUE ----------------

    for unique_columns in constraints.get("unique", []):

        # SQL permits multiple NULL values in UNIQUE columns.
        if any(row.get(column) is None for column in unique_columns):
            continue

        for existing in rows:

            if existing is ignore_row:
                continue

            if all(
                existing.get(column) == row.get(column)
                for column in unique_columns
            ):
                raise ValueError(
                    f"Duplicate UNIQUE value for {', '.join(unique_columns)}"
                )

    # ---------------- CHECK ----------------

    for check in constraints.get("checks", []):

        try:
            result = evaluate_check_expression(
                check["expression"],
                row
            )

        except (ValueError, TypeError, ZeroDivisionError) as error:
            raise ValueError(f"CHECK constraint error: {error}")

        if result is False:
            raise ValueError(
                f"CHECK constraint failed: {check['expression']}"
            )

    # ---------------- FOREIGN KEY ----------------

    for foreign_key in constraints.get("foreign_keys", []):

        local_columns = foreign_key["columns"]
        parent_table_name = foreign_key["referenced_table"]
        parent_columns = foreign_key["referenced_columns"]

        values = [row.get(column) for column in local_columns]

        # A NULL foreign key is allowed.
        if any(value is None for value in values):
            continue

        if parent_table_name not in database:
            raise ValueError(
                f"Referenced table '{parent_table_name}' does not exist"
            )

        parent_table = database[parent_table_name]

        found = any(
            all(
                parent_row.get(parent_column) == value
                for parent_column, value in zip(parent_columns, values)
            )
            for parent_row in parent_table["rows"]
        )

        if not found:
            raise ValueError(
                f"FOREIGN KEY constraint failed: "
                f"{parent_table_name}({', '.join(parent_columns)})"
            )


def validate_delete(table_name, row):

    for child_table_name, child_table in database.items():

        constraints = child_table.get("constraints", {})

        for foreign_key in constraints.get("foreign_keys", []):

            if foreign_key["referenced_table"] != table_name:
                continue

            for child_row in child_table["rows"]:

                matches = all(
                    child_row.get(local_column)
                    == row.get(parent_column)
                    for local_column, parent_column in zip(
                        foreign_key["columns"],
                        foreign_key["referenced_columns"]
                    )
                )

                if matches:
                    raise ValueError(
                        f"Cannot delete row: table "
                        f"'{child_table_name}' references it"
                    )


def validate_referenced_update(table_name, old_row, new_row):

    for child_table_name, child_table in database.items():

        constraints = child_table.get("constraints", {})

        for foreign_key in constraints.get("foreign_keys", []):

            if foreign_key["referenced_table"] != table_name:
                continue

            local_columns = foreign_key["columns"]
            parent_columns = foreign_key["referenced_columns"]

            changed = any(
                old_row.get(column) != new_row.get(column)
                for column in parent_columns
            )

            if not changed:
                continue

            for child_row in child_table["rows"]:

                references_old_row = all(
                    child_row.get(local_column)
                    == old_row.get(parent_column)
                    for local_column, parent_column in zip(
                        local_columns,
                        parent_columns
                    )
                )

                if references_old_row:
                    raise ValueError(
                        f"Cannot update referenced key: "
                        f"table '{child_table_name}' depends on it"
                    )


from database import database
