import dash
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_core_components as dcc
import dash_html_components as html
from dash.exceptions import PreventUpdate
import dash_table
import dash_bootstrap_components as dbc
import datetime as dt
import pandas as pd
import plotly.express as px
import os
import pandas as pd
import stat
from pathlib import Path
import callbacks as cb
import stat_scrapper.db_utils as db
import unidecode
import layouts

import stat_scrapper.boxscores as b

database_dir = Path('nba_dfs.db')
code_url = 'https://github.com/damancox/nba_daily_fantasy'

with db.create_connection('nba_dfs.db') as conn:
    refresh_q = """select max(date) from refresh_log"""
    refresh = pd.read_sql(refresh_q, conn)
    refresh_date = refresh.values[0][0]

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'NBA DFS'

server = app.server

app.layout = html.Div([
    
    dcc.Store(id='data-store'),
    
    html.Div([
        html.Div([ # Header
            html.A(dbc.Button('Code Repository', className='button'), 
                   href=code_url, target="_blank"),
            html.H1("NBA Daily Fantasy Viewer", className="header-title")
        ], className="header"),
        
        html.Div([  # Menu
            html.Div([
                html.Div("Today's Date:", className='menu-title'),
                html.Div(dt.date.today())
            ]),
            html.Div([
                html.Div("Pick Date", className='menu-title'),
                dcc.DatePickerSingle(id='date-picker', date=dt.date.today())
            ]),
            html.Div([
                html.Div("Data Refreshed:", className='menu-title'),
                html.Div(f"{refresh_date}")
            ])
        ], className='menu'),
        html.Div([ # tables holder
                  
            html.Div([ # player_table
                
                html.H5('Player Daily Fantasy Metrics'),
                html.Div([
                    layouts.player_table[0]
                ], className='card'),
                
            ], className='table-wrapper'),
            
            html.Div([
                
                html.H5('Scheduled Games'),
                html.Div([
                    layouts.team_table[0]
                ], className='card'),
                
                html.H5('Team Average DFS Score'),
                html.Div([
                    layouts.team_dfs_table[0]
                ], className='card'),
            ], className='team-wrapper'),
            
        ], className='row'),
        
        html.Div([
            html.H5('Player DFS Totals per Game'),
            html.Div([
                dcc.Graph(id='player-graph'),
            ], className='card')
            
        ], className='wrapper')
        
    ])
    
])

@app.callback(
    Output('data-store', 'data'),
    Input('date-picker', 'date')
)
def get_data(date):
    with db.create_connection(database_dir) as conn:
        df = cb.get_today_player_stats(conn, date=date)
        
        return df.to_dict('records')

@app.callback(
    [Output('player_table', 'columns'),
     Output('player_table', 'data'),
     Output('player_table', 'row_selectable')],
    [Input('data-store', 'data')]
)
def player_data(data):
    df = pd.DataFrame.from_dict(data)
    dfs_df = cb.aggregate_table_data(df)
    cols = [{"name": i, "id": i} for i in dfs_df.columns]
    table_data = dfs_df.to_dict('records')
    
    return cols, table_data, "multi",

@app.callback(
    [Output('team_table', 'columns'),
     Output('team_table', 'data')],
    [Input('date-picker', 'date')]
)
def update_team_table(date):
    q = """select date(Dates) as Date, 
           "Visitor/Neutral", 
           "Home/Neutral" 
           from schedule"""
    with db.create_connection('nba_dfs.db') as conn:
        sched = pd.read_sql(q, conn)
    
    df = sched[sched.Date == date]
    cols = [{"name": i, "id": i} for i in df.columns]
    data = df.to_dict('records')
    
    return cols, data

@app.callback(
    [Output('team_dfs_table', 'columns'),
     Output('team_dfs_table', 'data')],
    [Input('data-store', 'data')]
)
def update_team_dfs_table(data):
    df = pd.DataFrame.from_dict(data)
    dfs_df = cb.aggregate_team_dfs(df)
    cols = [{"name": i, "id": i} for i in dfs_df.columns]
    table_data = dfs_df.to_dict('records')
    
    return cols, table_data
    
@app.callback(
    Output('player-graph', 'figure'),
    [Input('data-store', 'data'),
     Input('player_table', 'derived_virtual_selected_rows'),
     Input('player_table', 'derived_virtual_data')]
)
def update_player_graph(data, row_inds, table_data):
    if len(row_inds) == 0:
        raise PreventUpdate
    else:
        box_df = pd.DataFrame.from_dict(data)
        print(box_df)
        boxscores = cb.calculate_player_dfs_scores(box_df)
        tbl_df = pd.DataFrame(table_data)
        idx = list(row_inds)
        player_list = tbl_df[tbl_df.index.isin(idx)]['player'].unique()
        graph_df = boxscores[boxscores['player'].isin(player_list)]
        graph_df.sort_values(by='date', inplace=True)
        graph_df.set_index('date', inplace=True)
        fig = px.line(graph_df, y='TOT_DFS', color='player', 
                      title='Daily Fantasy Score Totals')
        fig.update_xaxes(title_text='Date')
        fig.update_yaxes(title_text='DFS Score')
        fig.update_traces(mode='markers+lines')
        
        return fig

# Main
if __name__ == "__main__":
    app.run_server(debug=True)
