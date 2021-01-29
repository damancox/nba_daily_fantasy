#!/bin/bash

cd /code/nba_daily_fantasy
python3 update_db.py
git add .
git commit -m "Updated database”
git push
