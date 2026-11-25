from processing import command_analyzer

print("PythonSQL Terminal v1.0")

while True:
    command = input("sql> ")

    if command.strip().upper() == "EXIT":
        break

    print(command_analyzer(command))