import sqlite3
import uuid
from sqlite3 import Connection, DatabaseError
import os
from typing import Dict, Any

database : Connection = None

def connect(name):
    """
    Connects to a database
    :param name:
    :return: True if the connection is established
    """
    try:
        global database

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR,"..","..","database",name)

        database = sqlite3.connect(DB_PATH)

        return True
    except sqlite3.OperationalError:
        raise Exception("Error connecting to database")


def disconnect():
    """
    Disconnects from the database
    :return: None
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
        ValueError: If 'command' is not one of the allowed operations,
                    or if 'id' is missing for 'update' or 'delete'.
        DatabaseError:  If an error occurs with the database connection during
                        the execution of the command.

    Returns:
        A dictionary containing the result of the operation, typically
        including information like the number of rows affected.
    """
    if obj is None:
        raise ValueError("There has to be an object to modify")

    if command == "insert":
        _insert(table, obj)
    elif command == "update":
        _update(table, obj)
    elif command == "select":
        return _select(table, obj)
    else:
        raise ValueError("Invalid command")


def _insert(table, obj:Dict[str,Any]) -> None:
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
    except sqlite3.IntegrityError:
        database.rollback()
        raise Exception("Error inserting object")
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
    except sqlite3.IntegrityError:
        database.rollback()
        raise DatabaseError("Error updating object")
    finally:
        cursor.close()

def _delete(table, obj):
    if "id" not in obj:
        raise ValueError("There is no id in the object")

    obj_id = obj['id']
    sql_cmd = f"DELETE FROM {table} WHERE id = {obj_id}"

    try:
        cursor = database.cursor()
        cursor.execute(sql_cmd)
        database.commit()
    except sqlite3.IntegrityError:
        database.rollback()
        raise DatabaseError("Error deleting object")
    finally:
        cursor.close()

def _select(table, obj):
    clauses = []
    values = []

    for col, val in obj.items():
        clauses.append(f"({col}) = ?")
        values.append(val)

    where_clause = "AND ".join(clauses)

    sql_cmd = f"SELECT * FROM {table} WHERE {where_clause}"

    try:
        cursor = database.cursor()
        cursor.execute(sql_cmd, tuple(values))
        result = cursor.fetchall()
        if not result:
            return result
        col_names = [desc[0] for desc in cursor.description]

        results = [dict(zip(col_names, row)) for row in result]

        return results
    except sqlite3.IntegrityError:
        raise DatabaseError("Error selecting object")