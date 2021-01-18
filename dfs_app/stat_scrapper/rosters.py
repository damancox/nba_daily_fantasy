import pandas as pd 
from bs4 import BeautifulSoup
import requests
import os
import teams as ref
from errors import TeamAbbrevError
import sqlite3
import db_utils
from pathlib import Path

QUERY_DIR = Path('sql')

def get_roster(abbrev, year):
    """
    Get the roster of a specified team in a specified year.
    """
    # gets a list of team abbreviations to check against passed abbrev arg
    static_team_abbrev = ref.get_abbrevs()['abbrev'].to_list()
    # Raising error is passed abbrev not 3 characters or in team abbrev list
    if (len(abbrev) != 3) or (abbrev not in static_team_abbrev):
        raise TeamAbbrevError(abbrev)
    # converting to string if passed as int for adding to url
    if not isinstance(year, str):
        year = str(year)
    if abbrev == 'BKN':
        abbrev = 'BRK'
    elif abbrev == 'CHA':
        abbrev = 'CHO'
    elif abbrev == 'PHX':
        abbrev = 'PHO'
    # creating team specfic url to pull roster
    url = f'https://www.basketball-reference.com/teams/{abbrev}/{year}.html'
    #scraping and retr
    source = requests.get(url)
    soup = BeautifulSoup(source.content, 'html.parser')
    
    table = soup.find_all('table')
    header = table[0].find_all('th')
    rows = table[0].find_all('tr')

    #TODO really bad handling here if tables ever change
    cols = [x.text.strip() for x in header[1:9]]
    cols[5] = 'Cntry'
    
    roster = pd.DataFrame(columns=cols)
    for row in rows[1:]:
        row_data = row.find_all('td')
        player_data = pd.Series([x.text.strip() for x in row_data], index=cols)
        roster = roster.append(player_data, ignore_index=True)

    roster['abbrev'] = abbrev
    
    return roster

def update_roster_table(conn: sqlite3.Connection, year: str):
    """
    Creates the roster table in the databse.
    """
    abbrevs = ref.get_abbrevs()['abbrev']
    roster_df = pd.DataFrame()
    for abbrev in abbrevs:
        _temp = get_roster(abbrev, year)
        _temp['team'] = abbrev
        roster_df = roster_df.append(_temp)
    roster_df.to_sql('rosters', conn, if_exists='replace')
    print('Rosters succsesfully updated.')
    
    return