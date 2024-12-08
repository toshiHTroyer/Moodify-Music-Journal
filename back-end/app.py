"""
Music journal flask-based web application.
"""

import os
from flask import Flask, render_template, request, flash, redirect, url_for
import pymongo
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    current_user,
    logout_user,
)
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv, dotenv_values
import base64
import json
from requests import post, get
import certifi
from bson import ObjectId

load_dotenv()  # load environment variables from .env file

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

def create_app():
    """
    Create and configure the Flask application.
    returns: app: the Flask application object
    """

    app = Flask(__name__)
    bcrypt = Bcrypt(app)

    # load flask config from env variables
    config = dotenv_values()
    app.config.from_mapping(config)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
    db = cxn[os.getenv("MONGO_DBNAME")]

    try:
        cxn.admin.command("ping")
        print(" *", "Connected to MongoDB!")
    except Exception as e:
        print(" * MongoDB connection error:", e)

    cli_id = os.getenv("CLIENT_ID")
    cli_secret = os.getenv("CLIENT_SECRET")

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        user_data = db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(str(user_data["_id"]))
        return None

    # get spotify api access token
    def get_token():
        auth_string = cli_id + ":" + cli_secret
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": "Basic " + auth_base64,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        res = post(url, headers=headers, data=data)
        json_res = json.loads(res.content)
        token = json_res["access_token"]
        return token

    def get_auth_headers(token):
        return {"Authorization": "Bearer " + token}
    
    def search_for_song(token, song_name):
        url = "https://api.spotify.com/v1/search"
        headers = get_auth_headers(token)
        query = f"q={song_name}&type=track&limit=20"
        query_url = url + "?" + query

        res = get(query_url, headers=headers)
        json_res = json.loads(res.content).get("tracks", {}).get("items", [])

        if len(json_res) == 0:
            return None
        return ','.join([song["id"] for song in json_res])

    def get_songs(token, song_ids):
        if not song_ids:
            return []
        url = f"https://api.spotify.com/v1/tracks?ids={song_ids}"
        headers = get_auth_headers(token)
        res = get(url, headers=headers)
        json_res = json.loads(res.content)["tracks"]
        return json_res

    @app.route("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/home")
    def home_page():
        return render_template("home.html")
    
    @app.route("/recommendation")
    def recommendation():
        return render_template("recommendation.html")
    
    @app.route("/entry")
    def entry_page():
        return render_template("entry.html")
    
    @app.route("/entry-submission")
    def entry_submission_page():
        return render_template("entry-submission.html")

    @app.route("/search-songs", methods=["GET"])
    def search():
        token = get_token()
        song_name = request.args.get("songname", "")

        if not song_name:
            return render_template("search.html", songs=[])

        song_ids = search_for_song(token, song_name)
        songs = get_songs(token, song_ids)
        return render_template("search.html", songs=songs)

    # Authentication routes
    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            if not username or not password:
                flash("Missing required fields", "error")
                return redirect(url_for("signup"))

            # Check if user already exists
            if db.users.find_one({"username": username}):
                flash("User already exists", "error")
                return redirect(url_for("signup"))

            # Hash the password and save the user
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
            user = {"username": username, "password": hashed_password}
            db.users.insert_one(user)

            flash("User registered successfully!", "success")
            return redirect(url_for("login"))

        return render_template("signup.html")
    
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user_data = db.users.find_one({"username": username})

            if user_data and bcrypt.check_password_hash(user_data["password"], password):
                user = User(str(user_data["_id"]))
                login_user(user)
                return redirect(url_for("home_page"))

            flash("Invalid username or password.", "error")

        return render_template("login.html")
    
    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv('FLASK_PORT', '5000'))
    app.run(port=port, debug=(os.getenv('FLASK_ENV') == 'development'))
