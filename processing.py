
from sqlmodules.ddl import ddl_command
from sqlmodules.dml import dml_command
from sqlmodules.dql import dql_command
from sqlmodules.tcl import tcl_command
from sqlmodules.dcl import dcl_command


def command_analyzer(command):

    words = command.strip().split()

    if not words:
        return "ERROR: Empty command"

    operation = words[0].upper()

    # DDL
    if operation in ["CREATE", "ALTER", "DROP", "TRUNCATE"]:
        return ddl_command(command)

    # DML
    elif operation in ["INSERT", "UPDATE", "DELETE"]:
        return dml_command(command)

    # DQL
    elif operation == "SELECT":
        return dql_command(command)

    # TCL
    elif operation in ["BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT"]:
        return tcl_command(command)

    # DCL
    elif operation in ["GRANT", "REVOKE"]:
        return dcl_command(command)

    else:
        return "ERROR: Unsupported SQL command"
