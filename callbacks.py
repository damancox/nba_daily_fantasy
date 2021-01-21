import sqlite3
import pandas as pd 
import numpy as np
from stat_scrapper.db_utils import create_connection
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
from stat_scrapper.teams import get_abbrevs
from stat_scrapper.salaries import get_today_salaries
from unidecode import unidecode
from stat_scrapper.boxscores import update_boxscores_table

def unidecode_column(df, column):
    """
    Helper function to remove accents from text.
    """
    df[column] = df[column].apply(lambda x: unidecode(x))
    
    return df

def get_today_player_stats(conn, date=None):
    """
    Gets the boxscores of all players playing on the specified date.
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
    params = tuple(team_df['abbrev'].to_list())
    boxscore_q = f"""
    select * from boxscores where abbrev in {params}
    """
    boxscore_data = pd.read_sql(boxscore_q, conn)
    # removing accents from player names
    boxscore_data = unidecode_column(boxscore_data, 'player')
        
    return boxscore_data

def reformat_minutes_played(df, col='MP'):
    mins = df[col].apply(lambda x: x.split(':'))
    time_col = []
    for x in mins:
        x[0] = float(x[0])
        if len(x) == 2:
            x[1] = int(x[1]) / 60
            _ = x[0] + x[1]
            time_col.append(_)
        else:
            x.append(0)
            _ = x[0] + x[1]
            time_col.append(_)
    df['MP'] = time_col
    
    return df
 
def calculate_player_dfs_scores(df):
    """
    get player level dfs scores
    """
    # column subset to get dfs totals
    calc_cols = ['PTS', '3P', 'TRB', 'AST', 'STL', 'BLK', 'TOV']
    # converting to floats for calculation
    df[calc_cols] = df[calc_cols].astype(float)
    # scoring dict to apply to dataframe
    score_dict = {'PTS': 1, '3P': 0.5, 'TRB': 1.25, 'AST': 1.5, 
                  'STL': 2, 'BLK': 2, 'TOV': -0.5}
    # calculating DFS scoring
    for col in calc_cols:
        df[col] *= score_dict[col]
    # returning dataframe with dfs variables only
    dfs_cols = ['date', 'player', 'MP', 'PTS', '3P', 
                'TRB', 'AST', 'STL', 'BLK', 'TOV']
    dfs_df = df[dfs_cols]
    # aggregating total DFS score
    dfs_df['TOT_DFS'] = dfs_df.sum(axis=1)
    
    return dfs_df

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
    sal_df = get_today_salaries()[['Player', 'Today']]
    sal_df.columns = ['player', 'SALARY']
    sal_df['player'] = sal_df['player'].apply(lambda x: x.strip())
    sal_df['SALARY'] = (sal_df['SALARY']
                        .apply(lambda x: x.strip('$'))
                        .apply(lambda x: x.replace(',', ''))
                        .apply(lambda x: float(x)))
    # removing accents from player names
    sal_df = unidecode_column(sal_df, 'player')
    # inner merge drops injured and players not active
    merge_df = df.merge(sal_df, on='player', how='left')
    merge_df.fillna(0, inplace=True)
    
    return merge_df

def aggregate_table_data(boxscore_df):
    # adding below line in so names don't drop with acceents, needs to be 
    # handled better as this is duplicated code found the the merge_salaries
    # function.
    dfs_df = calculate_player_dfs_scores(boxscore_df)
    dfs_df = reformat_minutes_played(dfs_df)
    
    dfs_avg = calculate_avg_dfs_scores(dfs_df)
    dfs_std = calcualte_std_dfs_scores(dfs_df).fillna(0)
    
    dfs_agg = dfs_avg.merge(dfs_std[['player', 'STD_DFS']], on='player')
    dfs_agg = merge_salaries(dfs_agg)
    dfs_agg.sort_values(by='AVG_DFS', ascending=False, inplace=True)
    dfs_agg = dfs_agg.merge(boxscore_df[['player', 'team_name']], on='player')
    dfs_agg.insert(1, 'Team', dfs_agg.pop('team_name'))
    dfs_agg.drop_duplicates(inplace=True)
    
    table_df = dfs_agg[['player', 'Team', 'MP', 'AVG_DFS', 'STD_DFS', 'SALARY']]
    table_df['MULTI'] = round(table_df.AVG_DFS / (table_df.SALARY / 1000), 2)
    table_df['FPPM'] = round(table_df['AVG_DFS'] / table_df['MP'], 2)
    table_df.fillna(0, inplace=True)
    
    # re-ordering table
    table_df = (table_df[['player', 'Team', 'MP', 'AVG_DFS', 'FPPM', 
                         'STD_DFS', 'SALARY', 'MULTI']]
                .rename({'AVG_DFS': 'AVG', 'STD_DFS': 'STD'}, axis=1))
    
    return table_df

def calculate_team_dfs_scores(df):
    """
    get team level dfs scores
    """
    # column subset to get dfs totals
    calc_cols = ['PTS', '3P', 'TRB', 'AST', 'STL', 'BLK', 'TOV']
    # converting to floats for calculation
    df[calc_cols] = df[calc_cols].astype(float)
    # scoring dict to apply to dataframe
    score_dict = {'PTS': 1, '3P': 0.5, 'TRB': 1.25, 'AST': 1.5, 
                  'STL': 2, 'BLK': 2, 'TOV': -0.5}
    # calculating DFS scoring
    for col in calc_cols:
        df[col] *= score_dict[col]
    # returning dataframe with dfs variables only
    dfs_cols = ['team_name', 'MP', 'PTS', '3P', 
                'TRB', 'AST', 'STL', 'BLK', 'TOV']
    dfs_df = df[dfs_cols]
    # aggregating total DFS score
    dfs_df['TOT_DFS'] = dfs_df.sum(axis=1)
    dfs_df['TOT_DFS'] = dfs_df['TOT_DFS'] - dfs_df['MP']
    
    return dfs_df

def calculate_team_dfs_avg(df):
    avg_df = (df.groupby('team_name')['TOT_DFS'].mean()
              .reset_index()
              .dropna()
              .sort_values(by='TOT_DFS',ascending=False)
              .rename({'TOT_DFS': 'Average Score'}, axis=1)
              .round(2))
    
    return avg_df

def aggregate_team_dfs(boxscore_df):
    boxscore_df = reformat_minutes_played(boxscore_df)
    calc_df = (boxscore_df.groupby(['team_name', 'unique_id']).sum()
               .reset_index())
    dfs_df = calculate_team_dfs_scores(calc_df)
    dfs_avg = calculate_team_dfs_avg(dfs_df)
    dfs_avg.rename({'team_name': 'Team'}, axis=1, inplace=True)
    
    return dfs_avg


    