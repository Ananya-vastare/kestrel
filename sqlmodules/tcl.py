
import copy
from database import database

transaction_snapshot = None
savepoints = {}


def tcl_command(command):

    global transaction_snapshot

    operation = command.strip().rstrip(";").split()[0].upper()

    if operation == "BEGIN":

        transaction_snapshot = copy.deepcopy(database)
        savepoints.clear()

        return "Transaction started"

    elif operation == "SAVEPOINT":

        if transaction_snapshot is None:
            return "ERROR: No active transaction"

        name = command.strip().rstrip(";").split()[1]
        savepoints[name] = copy.deepcopy(database)

        return f"Savepoint '{name}' created"

    elif operation == "ROLLBACK":

        if transaction_snapshot is None:
            return "ERROR: No active transaction"

        parts = command.strip().rstrip(";").split()

        if len(parts) == 3 and parts[1].upper() == "TO":
            name = parts[2]

            if name not in savepoints:
                return "ERROR: Savepoint does not exist"

            database.clear()
            database.update(copy.deepcopy(savepoints[name]))

            return f"Rolled back to savepoint '{name}'"

        database.clear()
        database.update(copy.deepcopy(transaction_snapshot))

        transaction_snapshot = None
        savepoints.clear()

        return "Transaction rolled back"

    elif operation == "COMMIT":

        if transaction_snapshot is None:
            return "ERROR: No active transaction"

        transaction_snapshot = None
        savepoints.clear()

        return "Transaction committed"

    return "ERROR: Unsupported TCL command"
