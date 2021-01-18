from stat_scrapper.boxscores import update_boxscores_table
from stat_scrapper.db_utils import create_connection

with create_connection('nba_dfs.db') as conn:
    update_boxscores_table(conn, '2021')