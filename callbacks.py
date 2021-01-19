import sqlite3
import pandas as pd 
import numpy as np
from stat_scrapper.db_utils import create_connection
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
from stat_scrapper.teams import get_abbrevs
from stat_scrapper.salaries import get_today_salaries
import unidecode
from stat_scrapper.boxscores import update_boxscores_table

def get_today_player_stats(conn, date=None):
    """
    
    """
    if not date:
        date = dt.date.today().strftime('%Y-%m-%d')
    else:
        date = pd.to_datetime(date).strftime('%Y-%m-%d')
    schedule_q = f"""
    select *
    from schedule
    """
    # query the nba schedule
    df = pd.read_sql(schedule_q, conn)
    # ensure date field is datetime dtype
    df['Dates'] = df['Dates'].map(lambda x: pd.to_datetime(x))
    # getting games matching date variable
    df = df[df.Dates == date]
    # getting a list of the home and away teams for the date's games
    teams = df['Visitor/Neutral'].to_list() + df['Home/Neutral'].to_list()
    # Querying the tams table to ge the abbrevs to match as key
    abbrevs = get_abbrevs()
    # merging abbreviations with the team to query boxscore query params
    team_df = pd.DataFrame(teams, columns=['team_name'])
    team_df = team_df.merge(abbrevs, on='team_name')
    # getting teams that play today player boxscores for season
    boxscore_q = f"""
    select * from boxscores where abbrev in {tuple(team_df['abbrev'].to_list())}
    """
    boxscore_data = pd.read_sql(boxscore_q, conn)
    
    return boxscore_data
 
def calculate_dfs_scores(df):
    dfs_cols = ['date', 'player', 'PTS', '3P', 'TRB', 'AST', 'STL', 'BLK', 'TOV']
    calc_cols = dfs_cols[2:]
    calc_df = df[dfs_cols]
    calc_df[calc_cols] = calc_df[calc_cols].astype(float)
    score_dict = {'PTS': 1, '3P': 0.5, 'TRB': 1.25, 'AST': 1.5, 
                  'STL': 2, 'BLK': 2, 'TOV': -0.5}
    for col in calc_cols:
        calc_df[col] *= score_dict[col]
    
    calc_df['TOT_DFS'] = calc_df[calc_cols].sum(axis=1)
    
    return calc_df

def calculate_avg_dfs_scores(df):
    avg_df = (df.groupby('player').mean()
              .reset_index()
              .sort_values(by='TOT_DFS', ascending=False)
              .rename({'TOT_DFS': 'AVG_DFS'}, axis=1)
              .round(2))
    
    return avg_df

def calcualte_std_dfs_scores(df):
    std_df = (df.groupby('player').std()
              .dropna()
              .reset_index()
              .sort_values(by='TOT_DFS', ascending=False)
              .rename({'TOT_DFS': 'STD_DFS'}, axis=1)
              .round(2))
    
    return std_df

def merge_salaries(df):
    df['player'] = df['player'].apply(lambda x: unidecode.unidecode(x))
    sal_df = get_today_salaries()[['Player', 'Today']]
    sal_df.columns = ['player', 'SALARY']
    sal_df['player'] = sal_df['player'].apply(lambda x: x.strip())
    sal_df['SALARY'] = (sal_df['SALARY']
                        .apply(lambda x: x.strip('$'))
                        .apply(lambda x: x.replace(',', ''))
                        .apply(lambda x: float(x)))
    # inner merge drops injured and players not active
    merge_df = df.merge(sal_df, on='player', how='left')
    merge_df.fillna(0, inplace=True)
    
    return merge_df

def aggregate_table_data(boxscore_df):
    # adding below line in so names don't drop with acceents, needs to be 
    # handled better as this is duplicated code found the the merge_salaries
    # function.
    boxscore_df['player'] = boxscore_df['player'].apply(lambda x: unidecode.unidecode(x))
    dfs_df = calculate_dfs_scores(boxscore_df)
    dfs_avg = calculate_avg_dfs_scores(dfs_df)
    dfs_std = calcualte_std_dfs_scores(dfs_df).fillna(0)
    
    dfs_agg = dfs_avg.merge(dfs_std[['player', 'STD_DFS']], on='player')
    dfs_agg = merge_salaries(dfs_agg)
    dfs_agg['VALUE'] = round((dfs_agg['SALARY'] / (dfs_agg['STD_DFS'] / dfs_agg['AVG_DFS'])) / 1000, 2)
    dfs_agg['VALUE'].fillna(0, inplace=True)
    dfs_agg = dfs_agg.replace(np.inf, 0)
    dfs_agg.sort_values(by='VALUE', ascending=False, inplace=True)
    dfs_agg = dfs_agg.merge(boxscore_df[['player', 'team_name']], on='player')
    dfs_agg.insert(1, 'Team', dfs_agg.pop('team_name'))
    dfs_agg.drop_duplicates(inplace=True)
    
    return dfs_agg


    