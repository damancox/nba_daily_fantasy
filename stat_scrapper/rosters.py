import pandas as pd 
from bs4 import BeautifulSoup
import requests
import os
import static_team_references as ref
from errors import TeamAbbrevError

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