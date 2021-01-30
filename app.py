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
from stat_scrapper.teams import get_abbrevs

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
    dcc.Store(id='team-dfs'),
    
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
            
            html.Div([
                
                html.H5('Scheduled Games'),
                html.Div([
                    layouts.team_table[0]
                ], className='card'),
            ], className='team-wrapper'),
        
            html.Div([ # player_table
                
                html.H5('Player Daily Fantasy Metrics'),
                html.Div([
                    layouts.player_table[0]
                ], className='card'),
                
            ], className='table-wrapper'),
            
        ], className='row'),
        
        html.Div([
            html.H5('Player DFS Totals per Game'),
            html.Div([
                html.Div([
                    html.Div([
                        dcc.Dropdown(id='stat-drop',
                                    options=[{'label': i, 'value': i} 
                                            for i in ['MP', 'DFS']],
                                    value='DFS'),
                    ], style={'width': '30%', 'display': 'inline-block'}),
                    html.Div([
                        dcc.RadioItems(id='stat-level',
                        options=[{'label': i, 'value': i} 
                                for i in ['Per Game', '3 Game Avg']],
                        value='Per Game')
                    ], style={'width': '70%', 'float': 'right', 'display': 'inline-block'}),
                ]),
                dcc.Graph(id='player-graph'),
            ])
            
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
    [Input('data-store', 'data'),
     Input('team-dfs', 'data')]
)
def player_data(data, dfs):
    df = pd.DataFrame.from_dict(data)
    dfs_df = cb.aggregate_table_data(df)

    df2 = pd.DataFrame.from_dict(dfs)
    t1 = df2.iloc[:, 0:2]
    t1.rename({'Away': 'Team', 'Awy Avg': 'Avg'}, axis=1, inplace=True)
    t2 = df2.iloc[:, 2:4]
    t2.rename({'Home': 'Team', 'Hme Avg': 'Avg'}, axis=1, inplace=True)
    comp_df = pd.concat([t1, t2], axis=0)
    
    dfs_df = dfs_df.merge(comp_df, on='Team', how='left')
    dfs_df['Pct Team'] = round(dfs_df['AVG'] / dfs_df['Avg'], 2)
    dfs_df.drop('Avg', inplace=True, axis=1)
    cols = [{"name": i, "id": i} for i in dfs_df.columns]
    table_data = dfs_df.to_dict('records')
    return cols, table_data, "multi",

@app.callback(
    [Output('team_table', 'columns'),
     Output('team_table', 'data'),
     Output('team-dfs', 'data')],
    [Input('date-picker', 'date'),
     Input('data-store', 'data')]
)
def update_team_table(date, data):
    q = """select date(Dates) as Date, 
           "Visitor/Neutral", 
           "Home/Neutral" 
           from schedule"""
    with db.create_connection('nba_dfs.db') as conn:
        sched = pd.read_sql(q, conn)
    
    df = sched[sched.Date == date].drop('Date', axis=1)
    col_1 = df[['Visitor/Neutral']].rename({'Visitor/Neutral': 'Team'}, axis=1)
    col_2 = df[['Home/Neutral']].rename({'Home/Neutral': 'Team'}, axis=1)
    box_df = pd.DataFrame.from_dict(data)
    dfs_df = cb.aggregate_team_dfs(box_df)
    abb = get_abbrevs().rename({'team_name': 'Team'}, axis=1)
    t1 = abb.merge(col_1, on='Team', how='right').merge(dfs_df, on='Team', how='left').drop('Team', axis=1)
    t2 = abb.merge(col_2, on='Team', how='right').merge(dfs_df, on='Team', how='left').drop('Team', axis=1)
    t1.columns = ['Away', 'Awy Avg']
    t2.columns = ['Home', 'Hme Avg']
    team_df = pd.concat([t1, t2], axis=1)
    team_df['ABS_Diff'] = round(abs(team_df['Awy Avg'] - team_df['Hme Avg']), 1)
    team_df.sort_values(by='ABS_Diff', inplace=True, ascending=False)
    cols = [{"name": i, "id": i} for i in team_df.columns]
    data = team_df.to_dict('records')
    
    return cols, data, data

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
     Input('player_table', 'derived_virtual_data'),
     Input('stat-drop', 'value'),
     Input('stat-level', 'value')]
)
def update_player_graph(data, row_inds, table_data, stat, level):
    if len(row_inds) == 0:
        raise PreventUpdate
    else:
        box_df = pd.DataFrame.from_dict(data)
        boxscores = cb.calculate_player_dfs_scores(box_df)
        tbl_df = pd.DataFrame(table_data)
        idx = list(row_inds)
        player_list = tbl_df[tbl_df.index.isin(idx)]['player'].unique()
        graph_df = boxscores[boxscores['player'].isin(player_list)]
        graph_df.sort_values(by='date', inplace=True)
        graph_df.set_index('date', inplace=True)
        graph_df = cb.reformat_minutes_played(graph_df)
        print(graph_df)
        if stat == 'DFS':
            y_axis = 'TOT_DFS'
        elif stat == 'MP':
            y_axis = 'MP'
        if level == 'Per Game':
            pass
        elif level == '3 Game Avg':
            graph_df = (graph_df.groupby('player')[y_axis].rolling(3).mean()
                        .reset_index()
                        .set_index('date'))
        fig = px.line(graph_df, y=y_axis, color='player', 
                      title='Daily Fantasy Score Totals')
        fig.update_xaxes(title_text='Date')
        fig.update_yaxes(title_text=stat)
        fig.update_traces(mode='markers+lines')
        
        return fig

# Main
if __name__ == "__main__":
    app.run_server(debug=True)
