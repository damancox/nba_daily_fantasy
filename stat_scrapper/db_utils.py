import sqlite3
import pandas as pd
from boxscores import get_std_box_scores
from rosters import get_roster
from static_team_references import get_abbrevs
from pathlib import Path
import pandas as pd 
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
    
def create_teams_table(conn: sqlite3.Connection):
    """
    Creates teams table if not existing in database and inserts
    dataframe consisting of team abbreviations and names. Will
    not append if already exists.
    """
    abb_df = get_abbrevs()
    abbrev_create_tbl = QUERY_DIR.joinpath('create_team_table.sql')
    try:
        execute_query(abbrev_create_tbl, conn)
        abb_df.to_sql('teams', conn, if_exists='replace', index=False)
        print("Table: 'teams' succesfully created.")
    except sqlite3.Error as e:
        print(e)

    conn.commit()
    
    return    
    
def create_rosters_table(conn: sqlite3.Connection, year: str):
    create_roster_tbl = QUERY_DIR.joinpath('create_roster_table.sql')
    execute_query(create_roster_tbl, conn)
    abbrev_query = QUERY_DIR.joinpath('get_all_abbrevs.sql')
    abb_df = sql_to_df(abbrev_query, conn)
    roster_df = pd.DataFrame()
    for team in abb_df['abbrev']:
        team_df = get_roster(team, year)
        roster_df = roster_df.append(team_df)
    roster_df.to_sql('roster', conn, if_exists='replace')
    
    conn.commit()
    
    return

def create_agg_boxscores_table(conn: sqlite3.Connection, year: str):
    """
    Creates a boxscore table if not existing and inserts
    boxscores for all teams in specified year to database.
    Will not append, only add and replace.
    """
    create_teams_table(conn)
    create_box_tbl = QUERY_DIR.joinpath('create_boxscore_table.sql')
    execute_query(create_box_tbl, conn)
    abbrev_query = QUERY_DIR.joinpath('get_all_abbrevs.sql')
    abb_df = sql_to_df(abbrev_query, conn)
    agg_df = pd.DataFrame()
    for team in abb_df['abbrev']:
        print(f'Retrieving: {team}')
        team_df = get_std_box_scores(year=year, abbrev=team)
        team_df['abbrev'] = team
        agg_df = agg_df.append(team_df)
        time.sleep(2)
    agg_df.to_sql('boxscores', conn, if_exists='replace')
    
    conn.commit()
    
    return
    
    
    
