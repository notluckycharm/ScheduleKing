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
CLIENT_SECRET_FILE = 'json/client_secret_24926313134-10lhg1c7j7qgsm0ak32hqau8uj6al9ah.apps.googleusercontent.com (1).json'

# Direct to input page
@app.route('/')
def home():
    return render_template('home.html')

# Direct to authorization page
@app.route('/authorize/<role>')
def authorize(role):
    # save the role info for redirecting purpose
    session['user_role'] = role

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
    # get role info and redirect
    user_role = session.get('user_role')
    if user_role == 'host':
        return redirect('/host')
    elif user_role == 'invitee':
        return redirect('invitee')
    else:
        return redirect('/error') # Redirect to an error page or a default route

# two functions below with the help of ChatGPT
@app.route('/host', methods=['GET', 'POST'])
def host():
    if request.method == 'POST':
        duration = request.form.get('duration')
        dates = request.form.get('dates')
        work_hours_start = request.form.get('work_hours_start')
        work_hours_end = request.form.get('work_hours_end')
        available_slots = find_available_time_slots(duration, dates, work_hours_start, work_hours_end)
        return render_template('available_slots.html', slots=available_slots)

    return render_template('host_form.html')

@app.route('/invitee', methods=['GET', 'POST'])
def invitee():
    if request.method == 'POST':
        # Similar logic as in the host route
        duration = request.form.get('duration')
        dates = request.form.get('dates')
        work_hours_start = request.form.get('work_hours_start')
        work_hours_end = request.form.get('work_hours_end')
        available_slots = find_available_time_slots(duration, dates, work_hours_start, work_hours_end)
    return render_template('invitee_form.html')

# Function which uses API to find the first free time slot within constraints
# Return None if there's no free time slot
def find_available_time_slots(duration, dates, work_hours_start, work_hours_end):
    mtg_duration = int(duration)
    dates_list = [date.strip() for date in dates.split(',')]
    
    work_hours_start = datetime.strptime(request.form.get('work_hours_start'), '%H:%M').time()
    work_hours_end = datetime.strptime(request.form.get('work_hours_end'), '%H:%M').time()

    try:
        credentials_data = json.loads(session['credentials'])
        print("CREDENTIALS DATA:", credentials_data)
        credentials = Credentials.from_authorized_user_info(credentials_data)
        service = build('calendar', 'v3', credentials=credentials)

    # Continue with your code logic that requires the credentials...
    except KeyError:
        print("Session credentials not found.")
    except Exception as e:
        print(f"An error occurred while accessing session credentials: {e}")


    available_slots = []

    for date_str in dates_list:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.combine(date, work_hours_start)
        end_time = datetime.combine(date, work_hours_end)

        try:
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
        except Exception as e:
            print(f"An error occurred: {e}")
            continue

        current_time = start_time
        while current_time + timedelta(minutes=mtg_duration) <= end_time:
            slot_end_time = current_time + timedelta(minutes=mtg_duration)
            slot_free = True

            for event in events:
                event_start = datetime.fromisoformat(event['start']['dateTime'])
                event_end = datetime.fromisoformat(event['end']['dateTime'])
                if (event_start < slot_end_time and event_end > current_time):
                    slot_free = False
                    break

            if slot_free:
                available_slots.append(f"{current_time.strftime('%Y-%m-%d %H:%M')} - {slot_end_time.strftime('%H:%M')}")
            
            current_time += timedelta(minutes=mtg_duration)

    return available_slots

@app.route('/find_time', methods=['GET','POST'])
def find_time() :
    if request.method == 'POST':
        work_hours_start = request.form.get('work_hours_start')
        work_hours_end = request.form.get('work_hours_end')
        # Get user input from the form
        duration = request.form.get('duration')
        dates = request.form.get('dates')
        print(f"duration: {duration}")
        print(f"dates: {dates}")
        # Process user input and find the first free time slot
        first_free_time_slot = find_available_time_slots(
            duration,
            dates,
            work_hours_start, 
            work_hours_end
        )

        # Render the results page with the first free time slot
        return render_template('free_time.html', first_free_time_slot=first_free_time_slot)

    # Render the form page for user input
    return render_template('host_form.html')

"""
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
"""
if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'), debug=True)


