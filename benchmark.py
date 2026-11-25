
import time
import statistics
import psycopg2

from processing import command_analyzer
from database import database


# -------------------------------
# CONFIGURATION
# -------------------------------

POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "12345",
    "dbname": "python_sql_benchmark"
}

RECORD_COUNT = 10000
WARMUP_RUNS = 5
REPETITIONS = 30


# -------------------------------
# GENERATE DATA
# -------------------------------

students = [
    (
        i,
        f"Student{i}",
        18 + (i % 10),
        60.0 + (i % 40)
    )
    for i in range(1, RECORD_COUNT + 1)
]


# -------------------------------
# SET UP PYTHONSQL
# -------------------------------

print("Setting up PythonSQL...")

database.pop("students", None)

result = command_analyzer(
    "CREATE TABLE students (id INTEGER, name TEXT, age INTEGER, marks REAL)"
)

if "ERROR" in str(result).upper():
    raise RuntimeError(f"PythonSQL setup failed: {result}")

for index, student in enumerate(students, start=1):

    sql = (
        f"INSERT INTO students VALUES "
        f"({student[0]}, '{student[1]}', "
        f"{student[2]}, {student[3]})"
    )

    result = command_analyzer(sql)

    if "ERROR" in str(result).upper():
        raise RuntimeError(
            f"PythonSQL INSERT failed at record {index}: {result}"
        )

    if index % 1000 == 0:
        print(f"PythonSQL inserted {index} records")


# -------------------------------
# SET UP POSTGRESQL
# -------------------------------

print("\nSetting up PostgreSQL...")

connection = psycopg2.connect(**POSTGRES_CONFIG)
cursor = connection.cursor()

cursor.execute("DROP TABLE IF EXISTS students")

cursor.execute("""
    CREATE TABLE students (
        id INTEGER,
        name VARCHAR(50),
        age INTEGER,
        marks DOUBLE PRECISION
    )
""")

cursor.executemany(
    "INSERT INTO students VALUES (%s, %s, %s, %s)",
    students
)

connection.commit()

print("PostgreSQL inserted all records.")


# -------------------------------
# BENCHMARK FUNCTIONS
# -------------------------------

def measure_python_sql(query):

    timings = []

    # Warm-up
    for _ in range(WARMUP_RUNS):
        result = command_analyzer(query)

        if str(result).upper().startswith("ERROR"):
            raise RuntimeError(result)

    # Actual measurements
    for _ in range(REPETITIONS):

        start = time.perf_counter()

        result = command_analyzer(query)

        end = time.perf_counter()

        if str(result).upper().startswith("ERROR"):
            raise RuntimeError(result)

        timings.append((end - start) * 1000)

    return statistics.median(timings)


def measure_postgresql(query):

    timings = []

    # Warm-up
    for _ in range(WARMUP_RUNS):
        cursor.execute(query)
        cursor.fetchall()

    # Actual measurements
    for _ in range(REPETITIONS):

        start = time.perf_counter()

        cursor.execute(query)
        result = cursor.fetchall()

        end = time.perf_counter()

        timings.append((end - start) * 1000)

    return statistics.median(timings)


# -------------------------------
# RUN COMPARISON
# -------------------------------

queries = [
    "SELECT * FROM students",

    "SELECT * FROM students WHERE age >= 20",

    "SELECT * FROM students ORDER BY age DESC LIMIT 10",

    "SELECT age, COUNT(*) FROM students GROUP BY age",

    "SELECT AVG(marks) FROM students",

    "SELECT * FROM students WHERE marks >= 80 ORDER BY marks DESC LIMIT 10"
]


# -------------------------------
# DISPLAY RESULTS
# -------------------------------

print("\nPYTHONSQL vs POSTGRESQL BENCHMARK")
print("=" * 75)

print(f"Records: {RECORD_COUNT}")
print(f"Warm-up runs: {WARMUP_RUNS}")
print(f"Measured repetitions: {REPETITIONS}")

print("=" * 75)

results = []

for query in queries:

    print(f"\nRunning: {query}")

    python_time = measure_python_sql(query)
    postgres_time = measure_postgresql(query)

    results.append((query, python_time, postgres_time))

    print(f"PythonSQL:  {python_time:.4f} ms")
    print(f"PostgreSQL: {postgres_time:.4f} ms")

    if python_time < postgres_time:
        print("PythonSQL was faster in this test.")

    elif postgres_time < python_time:
        print("PostgreSQL was faster in this test.")

    else:
        print("Execution times were approximately equal.")


# -------------------------------
# FINAL SUMMARY
# -------------------------------

python_wins = sum(
    1 for _, p, pg in results if p < pg
)

postgres_wins = sum(
    1 for _, p, pg in results if pg < p
)

print("\n" + "=" * 75)
print("FINAL BENCHMARK SUMMARY")
print("=" * 75)

print(f"Dataset size: {RECORD_COUNT} records")
print(f"Total workloads: {len(queries)}")
print(f"PythonSQL wins: {python_wins}")
print(f"PostgreSQL wins: {postgres_wins}")

print("\nBenchmark completed!")

cursor.close()
connection.close()
