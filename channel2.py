## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
from flask_login import login_required
from openai import OpenAI

client = OpenAI(api_key='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')

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'AESF8wef734tWEDvisduvztwEGFqwi76f3wodsuv72qwfu7'

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://127.0.0.1:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '22334455'
CHANNEL_NAME = "The Lousy Channel"
CHANNEL_ENDPOINT = "http://localhost:5002"
CHANNEL_FILE = 'messages.json'

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
            "name": CHANNEL_NAME,
            "endpoint": CHANNEL_ENDPOINT,
            "authkey": CHANNEL_AUTHKEY}))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

@login_required
# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    return jsonify(read_messages())

@login_required
@app.route('/', methods=['POST'])
def handle_post_request():
    if not check_authorization(request):
        return "Invalid authorization", 400

    content = request.json

    # Check if the request is intended for the bot
    if content.get('content', '').startswith('/bot'):
        user_message = content['content'][5:]  # Extract message without '/bot '
        

        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message},
        ])
        messages = read_messages()
        messages.append({'content': content['content'], 'sender': content['sender'], 'timestamp': content['timestamp']})
        messages.append({'content': response.choices[0].message.content, 'sender': 'OpenAI', 'timestamp': content['timestamp']})
        save_messages(messages)
        return "Message saved, API responded", 200

    # Proceed with saving the message if not a bot command
    elif all(key in content for key in ['content', 'sender', 'timestamp']):
        messages = read_messages()
        messages.append({'content': content['content'], 'sender': content['sender'], 'timestamp': content['timestamp']})
        save_messages(messages)
        return "Message saved", 200

    else:
        return "Invalid request format", 400
def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

# Start development web server
if __name__ == '__main__':
    app.run(port=5002, debug=True)
