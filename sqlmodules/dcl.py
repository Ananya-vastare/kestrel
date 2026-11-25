
users = {
    "admin": {"ALL"}
}


def dcl_command(command):

    words = command.strip().rstrip(";").split()

    operation = words[0].upper()

    if operation == "GRANT":

        try:
            privilege = words[1].upper()
            username = words[3]

            if words[2].upper() != "TO":
                return "ERROR: Expected TO"

            users.setdefault(username, set())
            users[username].add(privilege)

            return f"{privilege} granted to {username}"

        except IndexError:
            return "ERROR: Invalid GRANT syntax"

    elif operation == "REVOKE":

        try:
            privilege = words[1].upper()
            username = words[3]

            if words[2].upper() != "FROM":
                return "ERROR: Expected FROM"

            if username not in users:
                return "ERROR: User does not exist"

            users[username].discard(privilege)

            return f"{privilege} revoked from {username}"

        except IndexError:
            return "ERROR: Invalid REVOKE syntax"

    return "ERROR: Unsupported DCL command"
