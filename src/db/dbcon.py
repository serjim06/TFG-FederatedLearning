import sqlite3
import uuid
from sqlite3 import Connection

database : Connection = None

def connect(name):
    try:
        global database
        database = sqlite3.connect("../database/" + name)
    except sqlite3.OperationalError:
        raise Exception("Error connecting to database")


def disconnect():
    global database
    database.close()

"""
Recibe un comando, la tabla y el objeto a modificar 
{
    "id": 1,
    "username": "admin"
    "password": "admin"
    "role": "admin"
}
"""
def command(command, table, obj):
    if obj is None:
        raise Exception("There has to be an object to modify")
    if command != "insert" or command != "update" or command != "delete":
        raise Exception("Invalid command")

    if command == "insert":
        insert(table, obj)


def insert(table, obj):
    """
    En el insert no se ponen la id del objeto, se genera automáticamente
    """
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

        return True
    except sqlite3.IntegrityError:
        database.rollback()
        raise Exception("Error inserting object")
    finally:
        cursor.close()

def update(table, obj):
    """
    :param table: tabla a modificar
    :param obj: objeto modificado
    :return: true si no hay erorres
    :raises Exception
    """

    obj_id = obj['id']
    values = ", ".join(f"{col} = ?" for col in obj.keys() if col != "id")

    sql_cmd = f"UPDATE {table} SET {values} WHERE id = ?"


    try:
        cursor = database.cursor()
        list_val = list(obj.values())
        cursor.execute(sql_cmd, tuple(list_val[1:] + list_val[:1]))
        database.commit()
        return True
    except sqlite3.IntegrityError:
        database.rollback()
        raise Exception("Error updating object")
    finally:
        cursor.close()

def delete(table, obj):
    """
    delete en la database
    :param table: tabla a modificar
    :param obj: objeto a eliminar
    :return: true si no hay erorres
    :raises Exception
    """

    obj_id = obj['id']
    sql_cmd = f"DELETE FROM {table} WHERE id = {obj_id}"

    try:
        cursor = database.cursor()
        cursor.execute(sql_cmd)
        database.commit()
        return True
    except sqlite3.IntegrityError:
        database.rollback()
        raise Exception("Error deleting object")
    finally:
        cursor.close()

def select(table, obj):
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
        raise Exception("Error selecting object")