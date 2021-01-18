import pandas as pd
from bs4 import BeautifulSoup
import requests
import numpy as np
import os

def get_abbrevs():
    """
    Retrieves a dictionary with team names and their correspoding abbreviation.
    """
    
    url = ('https://en.wikipedia.org/wiki/Wikipedia:WikiProject_National_Baske'
           'tball_Association/National_Basketball_Association_team_abbreviatio'
           'ns')
    
    source = requests.get(url)
    soup = BeautifulSoup(source.content, 'html.parser')
    
    table = soup.find_all('table')
    rows = table[0].find_all('tr')
    
    for row in rows:
        team = row.find_all('td')
    
    team_df = pd.DataFrame()
    for row in rows[1:]:
        team = row.find_all('td')
        abbrev = team[0].text.strip()
        name = team[1].text.strip()
        append_dict = {'team_name': name, 'abbrev': abbrev}
        team_df =  team_df.append(append_dict, ignore_index=True)
    
    return team_df

def update_teams_table(conn):
    abbrevs = get_abbrevs()
    abbrevs.to_sql('teams', conn, if_exists='replace')
    print('Teams succesfully udpated.')
    
    return
        