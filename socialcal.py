"""
socialcal.py

A gcal-based calendar generator based on a predefined
social media strategy. Differentiates between public
and private events with additional entries for
public events.
"""
from __future__ import print_function

import datetime as dt
import httplib2
import oauth2client
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools

from secrets import GOOGLE_CALENDAR_ID

# Google Auth constants
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = '../client_secret.json'
APPLICATION_NAME = 'Console App SocialCal'

try:
    import argparse
    arg_flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    arg_flags = None

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if arg_flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_info():
    """
    Gets the required information to create the schedule from
    user input. Prompts for variables based on a simple
    decision tree.
    """
    public = raw_input('Is this a public event? [Y/n]') or 'Y'
    is_public = (public[0].upper() != 'N')
    # Get data common between public and private events
    event_date = None
    while event_date is None:
        event_date_str = raw_input('What is the event date? (mm/dd/yyyy) ')
        try:
            event_date = dt.datetime.strptime(event_date_str, '%m/%d/%Y')
        except:
            event_date = None
        if event_date and (event_date < dt.datetime.now()):
            print('Event date must be today or later!')
            event_date = None
    location = raw_input('What city is the event in? ')
    if is_public:
        # We are getting data for a public event
        event_name = raw_input('What is the event name? ')
    else:
        event_name = 'Private event'
    return is_public, event_name, event_date, location

def build_calendar(is_public, event_date):
    """
    Returns a list of datetime objects to be added to the calendar.
    """

    """
    Social scheduling times
    Used to prevent collisions and floods
    Probably overthinking this, but if I ever want to automate,
    this is the way to go.
    """
    # Hour, 24-hour clock
    BOOKED_DAY_TIME = 18 # If event is booked after 6 PM, rotate to next day
    ONE_MONTH_TIME = 10
    TWO_WEEK_TIME = 9
    ONE_WEEK_TIME = 11
    THREE_DAY_TIME = 12
    DAY_OF_TIME = 8
    DAY_AFTER_TIME = 13

    print('Generating calendar...')
    the_calendar = []
    today = dt.datetime.now()
    # all events are broadcast on the signup date and on the event date
    # if past the scheduled hour, move signup post ahead one day
    if today.hour >= BOOKED_DAY_TIME:
        today += dt.timedelta(days=1)
    today = today.replace(hour=BOOKED_DAY_TIME, minute=0)
    the_calendar.append((today, 'Booking post',))
    # only add two events if the event date isn't today
    if event_date.date() != today.date():
        the_calendar.append(
            (dt.datetime.combine(event_date, dt.time(DAY_OF_TIME, 0)),
            'Event day post',))
    if is_public:
        # We only want to add dates that are today or after
        # normalizing one month to "four weeks"
        four_weeks = (event_date - dt.timedelta(days=28))
        if four_weeks.date() >= today.date():
            the_calendar.append(
                (dt.datetime.combine(four_weeks, dt.time(ONE_MONTH_TIME, 0)),
                'One month post',))
        two_weeks = (event_date - dt.timedelta(days=14))
        if two_weeks.date() >= today.date():
            the_calendar.append(
                (dt.datetime.combine(two_weeks, dt.time(TWO_WEEK_TIME, 0)),
                'Two week post',))
        one_week = (event_date - dt.timedelta(days=7))
        if one_week.date() >= today.date():
            the_calendar.append(
                (dt.datetime.combine(one_week, dt.time(ONE_WEEK_TIME, 0)),
                'One week post',))
        three_days = (event_date - dt.timedelta(days=3))
        if three_days.date() >= today.date():
            the_calendar.append(
                (dt.datetime.combine(three_days, dt.time(THREE_DAY_TIME, 0)),
                'Three days post',))
        day_after = (event_date + dt.timedelta(days=1))
        if day_after.date() >= today.date():
            the_calendar.append(
                (dt.datetime.combine(day_after, dt.time(DAY_AFTER_TIME, 0)),
                'Day after post',))
    print(the_calendar)
    return the_calendar

def serialize_datetime(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, dt.datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")

def interface(event_name, the_calendar):
    """Posts the calendar to the GCal API to create the events."""
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    print('Adding calendar entries to gcal...')

    for an_event in the_calendar:
        event = {
            'start': {
                'dateTime': serialize_datetime(an_event[0]),
                'timeZone': 'America/Chicago'
            },
            'end': {
                'dateTime': serialize_datetime(an_event[0] + dt.timedelta(minutes=30)),
                'timeZone': 'America/Chicago'
            },
            'summary': '%s for %s' % (an_event[1], event_name)
        }
        the_event = service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()

    print('Added %s events' % (len(the_calendar)))
    
def main():
    """The main function for standalone execution."""
    is_public, event_name, event_date, location  = get_info()
    event_cal = build_calendar(is_public, event_date)
    interface(event_name, event_cal)

if __name__ == '__main__':
    main()
