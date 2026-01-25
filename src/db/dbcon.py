import sqlite3
import uuid
import re
from sqlite3 import Connection, DatabaseError
import os
from typing import Dict, Any, Optional

database: Optional[Connection] = None

def connect(name):
    """
    Connects to a database
    Args:
        name: The name of the database.

    Returns:
        `True` if the database was created successfully.

    Raises:
        DatabaseError: if the database connection was not created.
    """
    try:
        global database

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR,"..","..","database",name)

        database = sqlite3.connect(DB_PATH)

        return True
    except sqlite3.OperationalError:
        raise DatabaseError("Error connecting to database")


def disconnect():
    """
    Disconnects from the database
    Returns:
        None
    """

    global database
    database.close()

def command(command: str, table, obj) -> Any:
    """
    Executes a database command (INSERT, UPDATE, or DELETE) on a specified table.

    The operation to execute is determined by the 'command' argument. For 'UPDATE'
    and 'DELETE' operations, the 'id' key within the 'obj' dictionary is mandatory
    to identify the target row.

    Args:
        command: The database operation to perform. Must be one of
                 "insert", "update", or "delete" (case-sensitive).
        table: The name of the table to perform the operation on.
        obj: A dictionary representing the data for the operation.
             For "update" and "delete", it MUST contain an "id" key
             for row identification. For "insert", it contains the data
             to be inserted, with or without the "id" key. If "id" is present,
             it will be ignored.

    Raises:
        ValueError: If there is no obj, 'command' is not one of the allowed operations,
                    or if 'id' is missing for 'update' or 'delete'.
        DatabaseError:  If an error occurs with the database connection during
                        the execution of the command.

    Returns:
            For "select", returns the row that fits to the clauses in a dictionary. If no rows are found, returns an
            empty dictionary. The other commands return None.
    """
    if obj is None:
        raise ValueError("There has to be an object to modify")

    if command == "insert":
       return _insert(table, obj)
    elif command == "update":
        _update(table, obj)
    elif command == "select":
        return _select(table, obj)
    elif command == "delete":
        _delete(table, obj)
    else:
        raise ValueError("Invalid command")


def _insert(table, obj:Dict[str,Any]):
    if "id" in obj:
        obj.pop("id")
    obj_id = uuid.uuid4().bytes
    keys = ", ".join(obj.keys())
    placeholders = ", ".join("?" for _ in (obj.values()))
    sql_cmd = f"INSERT INTO {table} (id, {keys}) VALUES (?, {placeholders})"
    values = list(obj.values())
    values.insert(0, obj_id)
    try:
        cursor = database.cursor()
        cursor.execute(sql_cmd, tuple(values))
        database.commit()
        cursor.close()
        return values
    except sqlite3.IntegrityError:
        database.rollback()
        raise DatabaseError("Error inserting object")
    finally:
        cursor.close()

def _update(table, obj):
    if "id" not in obj:
        raise ValueError("There is no id in the object")

    values = ", ".join(f"{col} = ?" for col in obj.keys() if col != "id")

    sql_cmd = f"UPDATE {table} SET {values} WHERE id = ?"

    try:
        cursor = database.cursor()
        list_val = list(obj.values())
        cursor.execute(sql_cmd, tuple(list_val[1:] + list_val[:1]))
        database.commit()
        cursor.close()
    except sqlite3.IntegrityError:
        database.rollback()
        raise DatabaseError("Error updating object")
    finally:
        cursor.close()

def _delete(table, where: dict):
    if not where:
        raise ValueError("WHERE clause cannot be empty")

    clauses = []
    values = []

    for key, value in where.items():
        clauses.append(f"{key} = ?")
        values.append(value)

    where_sql = " AND ".join(clauses)
    sql_cmd = f"DELETE FROM {table} WHERE {where_sql}"

    try:
        cursor = database.cursor()
        cursor.execute(sql_cmd, tuple(values))
        database.commit()
    except sqlite3.IntegrityError as e:
        database.rollback()
        raise DatabaseError("Error deleting object") from e
    finally:
        cursor.close()


def _select(table, obj):
    # Build filter object, but treat id == '*' as a request for all rows
    # (i.e. no WHERE clause).
    clauses = []
    values = []

    # Remove any id=='*' from filters so we can handle select-all
    filter_obj = {k: v for k, v in obj.items() if not (k == "id" and v == "*")}

    for col, val in filter_obj.items():
        # basic column name validation to avoid SQL injection via column names
        if not re.match(r'^[A-Za-z_]\w*$', col):
            raise ValueError(f"Invalid column name: {col}")
        clauses.append(f"{col} = ?")
        values.append(val)

    if clauses:
        where_clause = " AND ".join(clauses)
        sql_cmd = f"SELECT * FROM {table} WHERE {where_clause}"
    else:
        # no filters -> select all rows
        sql_cmd = f"SELECT * FROM {table}"

    try:
        cursor = database.cursor()
        if values:
            cursor.execute(sql_cmd, tuple(values))
        else:
            cursor.execute(sql_cmd)
        result = cursor.fetchall()
        if not result:
            cursor.close()
            return result
        col_names = [desc[0] for desc in cursor.description]

        results = [dict(zip(col_names, row)) for row in result]
        cursor.close()
        return results
    except sqlite3.IntegrityError:
        raise DatabaseError("Error selecting object")
    finally:
        try:
            cursor.close()
        except Exception:
            pass