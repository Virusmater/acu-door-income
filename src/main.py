from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta, timezone
import os
import pytz
from dotenv import load_dotenv

from src.event import Event

load_dotenv()
application = Flask(__name__)
local_datetime_format = '%Y-%m-%dT%H:%M'
token = os.getenv("TOKEN")
magic_word = os.getenv("MAGIC_WORD")
stager_token = os.getenv("STAGER_TOKEN")

@application.route("/")
def root():
    return "404"

@application.route("/"+ magic_word, methods = ['GET', 'POST'])
def main():
    to_time = request.args.get('to-time')
    if to_time:
        to_time = datetime.strptime(to_time, local_datetime_format)
        to_time = pytz.timezone('Europe/Amsterdam').localize(to_time)
    else:
        to_time = datetime.now()
    from_time = request.args.get('from-time')
    if from_time:
        from_time = datetime.strptime(from_time, local_datetime_format)
        from_time = pytz.timezone('Europe/Amsterdam').localize(from_time)
    else:
        from_time = to_time - timedelta(hours=6)

    event_id = request.args.get('event_id')
    if not event_id:
        event_id = -1
    else:
        event_id = int(event_id)

    users = "&users[]=door@acu.nl"
    order = "&order=descending"
    limit = "&limit=300"
    statuses = "&statuses[]=SUCCESSFUL"

    oldest_time = "&oldest_time=" + from_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    newest_time = "&newest_time=" + to_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    endpoint = "https://api.sumup.com/v0.1/me/transactions/history?" + users + order + limit + statuses + oldest_time + newest_time


    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        data = response.json()
        total_amount = sum(item['amount'] for item in data['items'])

    from_time_default = from_time.strftime(local_datetime_format)
    to_time_default = to_time.strftime(local_datetime_format)
    return render_template('main.html', sumup=total_amount, from_time = from_time_default,
                           to_time = to_time_default, events=get_events(), event_info=get_event_info(event_id))

def get_events():
    endpoint = "https://acu.stager.co/api/eventgroups/reportable"
    headers = {"Authorization": f"Basic {stager_token}"}
    response = requests.get(endpoint, headers=headers)
    event_list = []
    if response.status_code == 200:
        data = response.json()
        for event_json in data:
            event = Event()
            event.title = event_json['name_clean']
            event.event_id = event_json['id']
            event_list.append(event)
    return event_list

def get_event_info(id):
    endpoint = f"https://acu.stager.co/api/events/{id}/sales/days"
    headers = {"Authorization": f"Basic {stager_token}"}
    response = requests.get(endpoint, headers=headers)
    event = Event()
    event.event_id = id
    if response.status_code == 200:
        data = response.json()
        event.tickets_sold = data['periodOverview']['paidTickets']
        event.revenue = data['periodOverview']['revenue'] / 100
        event.profit = round(event.revenue - event.tickets_sold, 2)
    return event

@application.route("/robots.txt")
def robots_dot_txt():
    return "User-agent: *\nDisallow: /"
