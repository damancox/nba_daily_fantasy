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

import stat_scrapper.boxscores as b

cols_to_format = ['PTS', '3P', 'TRB', 'AST', 'STL', 'BLK', 'TOV',
                  'AVG_DFS', 'STD_DFS', 'SALARY', 'VALUE']

database_dir = Path('nba_dfs.db')

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
        html.Div([
            html.Div([ #figures
                dash_table.DataTable(id='player_table', 
                                    filter_action="native",
                                    sort_action="native",
                                    virtualization=True,
                                    fixed_rows={'headers': True, 'data': 0 },
                                    derived_virtual_selected_rows=[],
                                    style_as_list_view=True,
                                    style_cell={'padding': '10px'},
                                    style_cell_conditional=(
                                        [{'if': {'column_id': c},
                                         'textAlign': 'left'
                                         } for c in ['player', 'Team']]
                                        +
                                        [{'if': {'column_id': c},
                                          'width': '75px'
                                         } for c in cols_to_format]
                                        ),
                                    style_data_conditional=[
                                        {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(248, 248, 248)'
                                        }
                                        ],
                                    style_header={
                                       'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                        },
                                    )
            ], className='card'),
        ], className='wrapper'),
        html.Div([
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
def table_data(data):
    df = pd.DataFrame.from_dict(data)
    dfs_df = cb.aggregate_table_data(df)
    print(dfs_df)
    cols = [{"name": i, "id": i} for i in dfs_df.columns]
    table_data = dfs_df.to_dict('records')
    
    return cols, table_data, "multi",
    
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
        boxscores = cb.calculate_dfs_scores(box_df)
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
    app.run_server()
