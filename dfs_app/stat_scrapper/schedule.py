# Gets schedule for a team
# Looks for back to backs or possibly long road trips
# Something to handle possible load management


import pandas as pd
from bs4 import BeautifulSoup
import requests
import numpy as np
import os
import datetime as dt
import calendar
from .teams import get_abbrevs

def get_schedule(year, abbrev=None):
    """
    Pulls the nba schedule for each available month of the specified league
    year. Will aggregate all months into a single dataframe containing all 
    teams. Previous games will contain the score and attendance along with a 
    field containing links to the box score. Another function will scrape
    the data in these links.
    
    arguments:
    year -> league year to pull, use end year of season desired
    abbrev -> if not None, returns specified team only.
    """
    
    # getting months available for provided year
    url = f'https://www.basketball-reference.com/leagues/NBA_{year}_games.html'
    source = requests.get(url)
    soup = BeautifulSoup(source.content, 'html.parser')
    filt = soup.find_all('div', class_='filter')
    a_tag = filt[0].find_all('a')
    month_list = []
    for a in a_tag:
        month_list.append(a.text.lower())
        
    # looping through each month to get the schedule and aggregate into one df
    month_df_ls = []
    for month in month_list:
        url = (f'https://www.basketball-reference.com/leagues/NBA_{year}_games-'
               f'{month}.html')
        source = requests.get(url)
        soup = BeautifulSoup(source.content, 'html.parser')
        t_head = soup.find('thead')
        
        columns = []
        for th in t_head.find_all('th'):
            key = th.get_text()
            columns.append(key)
            # not including dates in headers since will add later
            headers = columns[1:]
        headers[5:7] = ['Box_Score', 'OT?']

        # gets data from table along with links to boxscores
        table_body = soup.find('tbody')
        table_rows = table_body.find_all('tr')
        table_data = pd.DataFrame(columns=headers)
        for row in table_rows:
            temp_data = row.find_all('td')
            row_data = pd.Series([x.text for x in temp_data], index=headers)
            for a_tags in row:
                tags = a_tags.find_all('a')
                for a in tags:
                    pre_mask = a.get('href')[0:4] == '/box'
                    post_mask = a.get('href')[-4:] == 'html'
                    if (pre_mask) & (post_mask):
                        row_data[5] = a.get('href')
            table_data = table_data.append(row_data, ignore_index=True)

        dates_col = soup.findAll('th', {'data-stat': 'date_game'})
        dates = []
        for x in dates_col:
            dates.append(x.get_text())

        table_data.insert(0, 'Dates', dates[1:])
        month_df_ls.append(table_data)
        agg_df = pd.concat(month_df_ls, axis=0)
        
    if abbrev:
        abbrev_df = get_abbrevs()
        team_name = abbrev_df[abbrev_df.abbrev == abbrev]['team_name'].values[0]
        vis_mask = (agg_df['Visitor/Neutral'] == team_name)
        hom_mask = (agg_df['Home/Neutral'] == team_name)
        agg_df = (agg_df[(vis_mask) | (hom_mask)]
                  .reset_index()
                  .drop('index', axis=1))
        
    agg_df['Dates'] = pd.to_datetime(agg_df.Dates)
    
    return agg_df

def update_schedule_table(conn, year):
    sched_df = get_schedule(year)
    sched_df.columns = ['Dates', 'Start (ET)', 'Visitor/Neutral', 'PTS_V', 
                        'Home/Neutral', 'PTS_H', 'Box_Score', 'OT?', 'Attend.', 
                        'Notes']
    sched_df.to_sql('schedule', conn, if_exists='replace')
    print('Schedule has been updated.')
    
    return