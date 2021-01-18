import sqlite3
import pandas as pd
from pathlib import Path
import time
import os

QUERY_DIR = Path('sql')

def sql_to_df(sql_path: str, conn: sqlite3.Connection, params: dict=None):
    with open(sql_path, 'r') as q:    
        query = q.read()
    if params:
        df = pd.read_sql(query, conn, **params)
    else:
        df = pd.read_sql(query, conn)
    
    return df

def execute_query(sql_path: str, conn=sqlite3.Connection):
    with open(sql_path, 'r') as q:
        query = q.read()
    try:
        conn.execute(query)
        print('Query executed.')
    except sqlite3.Error as e:
        print(e)

    return

def create_connection(db_name: str) -> sqlite3.Connection:
    try:
        p_path = Path(__file__).parent.parent
        write_path = p_path / 'db' / db_name
        db_file = os.path.abspath(write_path)
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)      
        return
    
    
    
