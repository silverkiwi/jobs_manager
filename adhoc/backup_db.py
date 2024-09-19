import sqlite3
from typing import List, Tuple


def export_core_data_to_sql(db_path: str, output_file: str) -> None:
    """
    Export core data from specified tables in a SQLite database to an SQL file.

    Args:
        db_path (str): Path to the SQLite database file.
        output_file (str): Path to the output SQL file.
    """
    core_tables: List[str] = ["workflow_staff"]

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            with open(output_file, "w", encoding="utf-8") as f:
                for table_name in core_tables:
                    f.write(f"-- Data for {table_name} --\n")

                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns: List[str] = [info[1] for info in cursor.fetchall()]

                    cursor.execute(f"SELECT * FROM {table_name};")
                    rows: List[Tuple] = cursor.fetchall()

                    for row in rows:
                        values: List[str] = [
                            (
                                "NULL"
                                if value is None
                                else (
                                    f"'{value.replace('', '')}'"
                                    if isinstance(value, str)
                                    else str(value)
                                )
                            )
                            for value in row
                        ]
                        insert_statement = (
                            f"INSERT INTO {table_name} "
                            f"({', '.join(columns)}) "
                            f"VALUES ({', '.join(values)});\n"
                        )
                        f.write(insert_statement)

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    DB_PATH: str = "../db.sqlite3"  # Path to your SQLite database file
    OUTPUT_FILE: str = "../core_data_backup.sql"  # Output file for the SQL statements
    export_core_data_to_sql(DB_PATH, OUTPUT_FILE)
