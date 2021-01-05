import pandas as pd 
import numpy as np
import sqlite3
from pathlib import Path
import db_utils as du

QUERY_DIR = Path('sql')

def read_player_stats(conn: sqlite3.Connection) -> pd.DataFrame:
    player_stats = QUERY_DIR.joinpath('get_player_stats.sql')
    with du.create_connection('nba_dfs.db') as conn:
        stat_df = du.sql_to_df(player_stats, conn)
    
    return stat_df 

def get_selectable_players(day=0):
    """
    Returns a list of players playing games today.
    Day argument will be added to datetime today method
    for getting games from future dates.
    """
    g

def calc_player_std_dev(df):
    