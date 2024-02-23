from flask import Flask, request, render_template, url_for, redirect
import requests
import urllib.parse
import datetime

from flask_login import login_user, logout_user, current_user

app = Flask(__name__)

HUB_AUTHKEY = '1234567890'
HUB_URL = 'http://localhost:5555'

CHANNELS = None
LAST_CHANNEL_UPDATE = None


from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# After initializing your Flask app
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# set secret
app.secret_key = 'wefwefuiowzefiwf76423987r6efqEwef2323'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Assuming you have a simple way to validate users, for example:
users = {'user1': {'password': 'password1'}}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def update_channels():
    global CHANNELS, LAST_CHANNEL_UPDATE
    if CHANNELS and LAST_CHANNEL_UPDATE and (datetime.datetime.now() - LAST_CHANNEL_UPDATE).seconds < 60:
        return CHANNELS
    # fetch list of channels from server
    response = requests.get(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY})
    if response.status_code != 200:
        return "Error fetching channels: "+str(response.text), 400
    channels_response = response.json()
    if not 'channels' in channels_response:
        return "No channels in response", 400
    CHANNELS = channels_response['channels']
    LAST_CHANNEL_UPDATE = datetime.datetime.now()
    return CHANNELS


@app.route('/')
def home_page():
    # fetch list of channels from server
    return render_template("home.html", channels=update_channels())


@app.route('/show')
def show_channel():
    # Check if the user is not authenticated
    if not current_user.is_authenticated:
        # Redirect to the login page if the user is not authenticated
        return render_template("login.html")

    # Proceed with fetching list of messages from channel if the user is authenticated
    show_channel = request.args.get('channel', None)
    if not show_channel:
        return "No channel specified", 400
    channel = None
    for c in update_channels():
        if c['endpoint'] == urllib.parse.unquote(show_channel):
            channel = c
            break
    if not channel:
        return "Channel not found", 404
    response = requests.get(channel['endpoint'], headers={'Authorization': 'authkey ' + channel['authkey']})
    if response.status_code != 200:
        return "Error fetching messages: " + str(response.text), 400
    messages = response.json()
    return render_template("channel.html", channel=channel, messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            next_page = request.args.get('next') or url_for('home_page')
            return redirect(next_page)
        else:
            return 'Invalid username or password'
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home_page'))



@app.route('/post', methods=['POST'])
def post_message():
    # send message to channel
    post_channel = request.form['channel']
    if not post_channel:
        return "No channel specified", 400
    channel = None
    for c in update_channels():
        if c['endpoint'] == urllib.parse.unquote(post_channel):
            channel = c
            break
    if not channel:
        return "Channel not found", 404
    message_content = request.form['content']
    message_sender = current_user.id
    message_timestamp = datetime.datetime.now().isoformat()
    response = requests.post(channel['endpoint'],
                             headers={'Authorization': 'authkey ' + channel['authkey']},
                             json={'content': message_content, 'sender': message_sender, 'timestamp': message_timestamp})
    if response.status_code != 200:
        #
        return "Error posting message: "+str(response.text), 400
    return redirect(url_for('show_channel')+'?channel='+urllib.parse.quote(post_channel))

# Start development web server
if __name__ == '__main__':
    app.run(port=5005, debug=True)
