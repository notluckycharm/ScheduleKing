"""
This file contains the main content for the ScheduleKing App, an Alternative 
Scheduling App which tells YOU when you will be meeting, whether you like
it, or not.
"""

from flask import Flask, render_template, redirect, request, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Google Calendar API Scope
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.freebusy',
    # Add more scopes as needed
    'https://www.googleapis.com/auth/calendar.freebusy',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.events.owned']

# Path to the client secret JSON file downloaded from the Google Cloud Console
CLIENT_SECRET_FILE = 'json/client_secret_24926313134-10lhg1c7j7qgsm0ak32hqau8uj6al9ah.apps.googleusercontent.com.json'
# Define working hours (based on user input from HTML form)
working_hours_start = datetime.strptime('09:00', '%H:%M').time()
working_hours_end = datetime.strptime('17:00', '%H:%M').time()

# Direct to input page
@app.route('/')
def home():
    return render_template('home.html')

# Direct to authorization page
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, 
        scopes=SCOPES,
        redirect_uri='https://127.0.0.1:5000/callback'

    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

# Callback Google Calendar API
@app.route('/callback')
def callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri='https://127.0.0.1:5000/callback'
    )
    flow.fetch_token(authorization_response=request.url)
    session['credentials'] = flow.credentials.to_json()
    return redirect('/find_time')

# Function which uses API to find the first free time slot within constraints
# Return None if there's no free time slot
def find_first_free_time_slot(work_begin,work_end,mtg_duration,dates):
    # Convert duration to integer
    mtg_duration = int(mtg_duration)

    # Parse dates into a list
    dates_list = [date.strip() for date in dates.split(',')]

    # Initialize Google Calendar API credentials (you may need to adjust this based on your setup)
    # Deserialize the JSON string stored in session['credentials']
    credentials_data = json.loads(session['credentials'])

    # Create credentials object from the deserialized data
    credentials = Credentials.from_authorized_user_info(credentials_data)
    service = build('calendar', 'v3', credentials=credentials)

    events = []
    # Iterate through each date
    for date_str in dates_list:
        # Parse date string to datetime object
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Define start and end times for the date
        start_time = datetime.combine(date, work_begin)
        end_time = datetime.combine(date, work_end)
        print("Hi!")
        try:
            # Make API call to list events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            # Print the response to inspect its structure and content
            print("EVENTS", events_result)

            # Process API response
            events = events_result.get('items', [])

        except Exception as e:
            # Handle the exception
            print(f"An error occurred: {e}")


        # Find the first available time slot within working hours
        current_time = start_time
        while current_time + timedelta(minutes=mtg_duration) <= end_time:
            slot_end_time = current_time + timedelta(minutes=mtg_duration)
            slot_free = True

            # Check if the time slot overlaps with any existing event
            for event in events:
                event_start = datetime.fromisoformat(event['start']['dateTime'])
                event_end = datetime.fromisoformat(event['end']['dateTime'])

                if (event_start < slot_end_time and event_end > current_time):
                    slot_free = False
                    break
            
            # If the time slot is free, return it
            if slot_free:
                return f"{current_time.strftime('%Y-%m-%d %H:%M')} - {slot_end_time.strftime('%H:%M')}"

            # Move to the next time slot
            current_time += timedelta(minutes=mtg_duration)

    # If no free time slot is found, return None
    return None

@app.route('/find_time', methods=['GET','POST'])
def find_time() :
    if request.method == 'POST':
        # Get user input from the form
        duration = request.form.get('duration')
        dates = request.form.get('dates')

        # Process user input and find the first free time slot
        first_free_time_slot = find_first_free_time_slot(
            working_hours_start, 
            working_hours_end, 
            duration, 
            dates
        )

        # Render the results page with the first free time slot
        return render_template('free_time.html', first_free_time_slot=first_free_time_slot)

    # Render the form page for user input
    return render_template('input_form.html')

# TODO: Check availability
@app.route('/check_availability')
def check_availability():
    credentials = Credentials.from_authorized_user_info(session['credentials'])
    service = build('calendar', 'v3', credentials=credentials)

    # Example: Check availability for the next 24 hours
    now = datetime.datetime.utcnow()
    end_time = now + datetime.timedelta(hours=24)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now.isoformat() + 'Z',
        timeMax=end_time.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])

    # Process events and determine availability
    return render_template('availability.html', events=events)

# TODO
@app.route('/host', methods=['GET', 'POST'])
def host():
    if request.method == 'POST':
        # Process and handle the form data
        # ... [Your form processing logic] ...
        return redirect('/some_result_page')

    return render_template('host_form.html')  # Render the host form

@app.route('/invitee', methods=['GET', 'POST'])
def invitee():
    if request.method == 'POST':
        # Process and handle the form data for invitee
        # ... [Your form processing logic] ...
        return redirect('/some_result_page')

    return render_template('invitee_form.html')  # Render the invitee form

if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'), debug=True)


