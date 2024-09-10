import sqlite3


def export_core_data_to_sql(db_path, output_file):
    core_tables = ["workflow_staff"]

    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(output_file, "w") as f:
        # Iterate through core tables only
        for table_name in core_tables:
            f.write(f"-- Data for {table_name} --\n")

            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [info[1] for info in cursor.fetchall()]

            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()

            for row in rows:
                values = []
                for value in row:
                    if isinstance(value, str):
                        value = value.replace("'", "''")
                        values.append(f"'{value}'")
                    elif value is None:
                        values.append("NULL")
                    else:
                        values.append(str(value))
                values_str = ", ".join(values)
                insert_statement = (
                    f"INSERT INTO {table_name} "
                    f"({', '.join(columns)}) "
                    f"VALUES ({values_str});\n"
                )
                f.write(insert_statement)

    # Close the database connection
    conn.close()


if __name__ == "__main__":
    db_path = "db.sqlite3"  # Path to your SQLite database file
    output_file = "core_data_backup.sql"  # Output file for the SQL statements
    export_core_data_to_sql(db_path, output_file)
