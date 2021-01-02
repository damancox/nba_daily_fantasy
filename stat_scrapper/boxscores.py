
import pandas as pd
from bs4 import BeautifulSoup
import requests
import numpy as np
import os
import datetime as dt
import calendar
from schedule import get_schedule
from static_team_references import get_abbrevs
import numpy as np

def get_std_box_scores(year, abbrev=None):
    """
    Pulls and aggregates boxscores of all games within a year or 
    of specified team. Pulls standard boxscore of both teams to aggregate
    together returning one dataframe of all games. Each game is given
    its own unique id.
    """
    sched = get_schedule(year, abbrev)
    prepend = 'https://www.basketball-reference.com'
    
    
    links = [prepend + x for x in sched['Box_Score'] if len(x) > 0]
    dates = [x for x in sched['Dates'][:len(links)]]
    
    master_df = pd.DataFrame()
    for link, date in zip(links, dates):
        source = requests.get(link)
        soup = BeautifulSoup(source.content, 'html.parser')

        team_headings = soup.find_all('div', class_='section_heading')

        # getting names of teams tabled
        team_1 = team_headings[3].text.strip()[:-6]
        team_2 = team_headings[11].text.strip()[:-6]
        #handling for if OT changing sequence length
        ot = None
        if team_2 == '':
            team_2 = team_headings[12].text.strip()[:-6]
            ot = True
            
        abbrev_df = get_abbrevs()
        
        t1_abbrev = abbrev_df[abbrev_df['team_name'] == team_1]['abbrev'].values[0]
        t2_abbrev = abbrev_df[abbrev_df['team_name'] == team_2]['abbrev'].values[0]
        # getting std and adv tables for both teams
        tables = soup.find_all('table', class_='sortable')

        # getting the columns and players for both teams
        team_1_std = tables[0]
        if ot:
            team_2_std = tables[9]
        else:
            team_2_std = tables[8]
        # 7 and 15 for advanced

        head_1 = []
        for th in team_1_std.find_all('th'):
            head_1.append(th.text)
            
        head_2 = []
        for th in team_2_std.find_all('th'):
            head_2.append(th.text)

        cols = head_1[3:23]
        t1_players = head_1[23:28] + head_1[49:]
        t2_players = head_2[23:28] + head_2[49:]

        # getting the table data for both teams
        t1_df = pd.DataFrame(columns=cols)
        rows = team_1_std.find_all('tr')
        for row in rows[2:]:
            temp_td = row.find_all('td')
            temp_row = [x.text for x in temp_td]
            if len(temp_row) < 1:
                pass
            else:
                if len(temp_row) == 1:
                    temp_row = list(np.repeat(0, 20))
                temp_ser = pd.Series(temp_row, index=cols)
                t1_df = t1_df.append(temp_ser, ignore_index=True)
                
        t1_df.insert(0, 'player', t1_players)

        t2_df = pd.DataFrame(columns=cols)
        rows = team_2_std.find_all('tr')
        for row in rows[2:]:
            temp_td = row.find_all('td')
            temp_row = [x.text for x in temp_td]
            if len(temp_row) < 1:
                pass
            else:
                if len(temp_row) == 1:
                    temp_row = list(np.repeat(0, 20))
                temp_ser = pd.Series(temp_row, index=cols)
                t2_df = t2_df.append(temp_ser, ignore_index=True)
                
        t2_df.insert(0, 'player', t2_players)

        t1_df['team_name'] = team_1
        t2_df['team_name'] = team_2

        agg_df = (pd.concat([t1_df, t2_df], axis=0)
                  .reset_index()
                  .drop('index', axis=1))
        agg_df['date'] = date.strftime('%Y-%m-%d') 
        agg_df['unique_id'] = (agg_df['date']
                                + t1_abbrev + t2_abbrev)
        
        master_df = master_df.append(agg_df)
        master_df = master_df[master_df.player != 'Team Totals']
        
    return master_df


    
    
    