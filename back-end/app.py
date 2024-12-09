"""
Music journal flask-based web application.
"""

import os
import datetime
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
from collections import Counter

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
        
        songs = []
        for track in json_res:
            songs.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "spotify_id": track["id"],  # Spotify track ID for embedding
                "spotify_url": track["external_urls"]["spotify"],  # Full Spotify link
            })
        return songs


    # def get_songs(token, song_ids):
    #     if not song_ids:
    #         return []
    #     url = f"https://api.spotify.com/v1/tracks?ids={song_ids}"
    #     headers = get_auth_headers(token)
    #     res = get(url, headers=headers)
    #     json_res = json.loads(res.content)["tracks"]
    #     return json_res

    @app.route("/")
    def index():
        return redirect(url_for("login"))


    @app.route("/home")
    @login_required
    def home_page():
        user_id = current_user.id
        entries = list(db.entries.find({"user_id": user_id}).sort("created_at", -1))  # Sort by latest entry first

        if entries:
            moods = [entry.get("mood", "Unknown mood") for entry in entries]
            timestamps = [entry.get("created_at").strftime("%Y-%m-%d %H:%M:%S") for entry in entries]
            top_mood = Counter(moods).most_common(1)[0][0]  # Most common mood
            latest_mood = moods[0]  # Latest mood
        else:
            moods = []
            timestamps = []
            top_mood = "No data"
            latest_mood = "No data"

        formatted_entries = [
            {
                "id": str(entry["_id"]), 
                "time": entry.get("created_at").strftime("%I:%M %p") if entry.get("created_at") else "Unknown time",
                "song": entry.get("track_name", "Unknown song"),
                "mood": entry.get("mood", "Unknown mood"),
            }
            for entry in entries
        ]

        return render_template(
            "home.html",
            entries=formatted_entries,
            moods=moods,
            timestamps=timestamps,
            top_mood=top_mood,
            latest_mood=latest_mood
        )



    
    @app.route("/entry", methods=["GET", "POST"])
    def entry_page():
        token = get_token()
        song_name = request.args.get("songname", "")
        songs = []

        if song_name:
            song_ids = search_for_song(token, song_name)
            if song_ids:
                songs = get_songs(token, song_ids)  # Includes Spotify track ID

        return render_template("entry.html", songs=songs, searched=song_name)

    @app.route("/entry-submission", methods=["GET", "POST"])
    def entry_submission_page():
        if request.method == "POST":
            # Retrieve song data from the POST request
            track_name = request.form.get("track_name")
            track_artist = request.form.get("track_artist")
            track_id = request.form.get("track_id")

            # Pass the selected song to the template
            return render_template(
                "entry-submission.html",
                track_name=track_name,
                track_artist=track_artist,
                track_id=track_id,
            )

        # Default GET behavior (if accessed without a POST request)
        return redirect(url_for("entry_page"))
    
    @app.route("/save-entry", methods=["POST"])
    @login_required
    def save_entry():
        # Get data from the form submission
        track_name = request.form.get("track_name")
        track_artist = request.form.get("track_artist")
        track_id = request.form.get("track_id")
        mood = request.form.get("mood")

        if not track_name or not track_artist or not track_id or not mood:
            flash("All fields are required!", "error")
            return redirect(url_for("entry_submission_page"))

        # Create the entry data
        entry = {
            "user_id": current_user.id,  # Add the user ID here
            "track_name": track_name,
            "track_artist": track_artist,
            "track_id": track_id,
            "mood": mood,
            "created_at": datetime.datetime.now(),
        }

        # Save to database
        db.entries.insert_one(entry)

        flash("Entry saved successfully!", "success")
        return redirect(url_for("home_page"))

    @app.route("/delete-entry/<entry_id>", methods=["POST"])
    @login_required
    def delete_entry(entry_id):
        try:
            print(f"Attempting to delete entry with ID: {entry_id} for user: {current_user.id}")
            result = db.entries.delete_one({"_id": ObjectId(entry_id), "user_id": current_user.id})
            if result.deleted_count > 0:
                flash("Entry deleted successfully!", "success")
            else:
                flash("Failed to delete entry or entry not found.", "error")
        except Exception as e:
            print(f"Error deleting entry: {e}")
            flash("An error occurred while deleting the entry.", "error")
        return redirect(url_for("home_page"))
 

        
    @app.route("/recommendation")
    def recommendation():
        return render_template("recommendation.html")



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
