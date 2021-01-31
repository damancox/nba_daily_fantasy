import dash_table

team_table = dash_table.DataTable(id='team_table',
                                    sort_action="native",
                                    virtualization=True,
                                    fixed_rows={'headers': True, 'data': 0},
                                    derived_virtual_selected_rows=[],
                                    style_as_list_view=True,
                                    style_cell={'padding': '10px'},
                                    style_data_conditional=[
                                        {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(248, 248, 248)'
                                        }
                                    ],
                                    style_header={
                                       'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                    },),

team_dfs_table = dash_table.DataTable(id='team_dfs_table',
                                    sort_action="native",
                                    virtualization=True,
                                    fixed_rows={'headers': True, 'data': 0},
                                    derived_virtual_selected_rows=[],
                                    style_as_list_view=True,
                                    style_cell={'padding': '10px'},
                                    style_data_conditional=[
                                        {'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(248, 248, 248)'
                                        }
                                    ],
                                    style_header={
                                       'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                    },),

player_table = dash_table.DataTable(id='player_table', 
                                    filter_action="native",
                                    sort_action="native",
                                    virtualization=True,
                                    fixed_rows={'headers': True, 'data': 0},
                                    derived_virtual_selected_rows=[],
                                    style_as_list_view=True,
                                    style_cell={'padding': '10px'},
                                    style_cell_conditional=(
                                        [{'if': {'column_id': c},
                                         'textAlign': 'left'
                                         } for c in ['player', 'Team']]
                                        +
                                        [{'if': {'column_id': c},
                                          'width': '85px'
                                         } for c in ['Pct Team']]
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
                                    ),