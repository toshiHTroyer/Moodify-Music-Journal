"""
Music journal flask-based web application.
"""

import os
import datetime
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
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
from datetime import datetime as dt

load_dotenv()


class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


def create_app():
    app = Flask(__name__)
    bcrypt = Bcrypt(app)

    # load flask config from env variables
    config = dotenv_values()
    app.config.from_mapping(config)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret_key")

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

    def get_token():
        try:
            auth_string = cli_id + ":" + cli_secret
            auth_bytes = auth_string.encode("utf-8")
            auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

            url = "https://accounts.spotify.com/api/token"
            headers = {
                "Authorization": "Basic " + auth_base64,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"grant_type": "client_credentials"}
            res = post(url, headers=headers, data=data)
            if res.status_code != 200:
                print(f"Token error: {res.content}")
                return None
            token = json.loads(res.content)["access_token"]
            return token
        except Exception as e:
            print(f"Get token error: {str(e)}")
            return None

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
        return ",".join([song["id"] for song in json_res])

    def get_songs(token, song_ids):
        if not song_ids:
            return []
        url = f"https://api.spotify.com/v1/tracks?ids={song_ids}"
        headers = get_auth_headers(token)
        res = get(url, headers=headers)
        json_res = json.loads(res.content)["tracks"]

        songs = []
        for track in json_res:
            songs.append(
                {
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "spotify_id": track["id"],
                    "spotify_url": track["external_urls"]["spotify"],
                }
            )
        return songs

    @app.route("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/home")
    @login_required
    def home_page():
        user_id = current_user.id
        entries = list(db.entries.find({"user_id": user_id}).sort("created_at", -1))

        if entries:
            moods = [entry.get("mood", "Unknown mood") for entry in entries]
            timestamps = [
                entry.get("created_at").strftime("%Y-%m-%d %H:%M:%S")
                for entry in entries
                if entry.get("created_at")
            ]
            top_mood = Counter(moods).most_common(1)[0][0] if moods else "No data"
            latest_mood = moods[0] if moods else "No data"
        else:
            moods = []
            timestamps = []
            top_mood = "No data"
            latest_mood = "No data"

        formatted_entries = [
            {
                "id": str(entry["_id"]),
                "time": (
                    entry.get("created_at").strftime("%I:%M %p")
                    if entry.get("created_at")
                    else "Unknown time"
                ),
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
            latest_mood=latest_mood,
        )

    @app.route("/entry", methods=["GET", "POST"])
    def entry_page():
        token = get_token()
        song_name = request.args.get("songname", "")
        songs = []
        if song_name and token:
            song_ids = search_for_song(token, song_name)
            if song_ids:
                songs = get_songs(token, song_ids)
        return render_template("entry.html", songs=songs, searched=song_name)

    @app.route("/entry-submission", methods=["GET", "POST"])
    def entry_submission_page():
        if request.method == "POST":
            track_name = request.form.get("track_name")
            track_artist = request.form.get("track_artist")
            track_id = request.form.get("track_id")

            return render_template(
                "entry-submission.html",
                track_name=track_name,
                track_artist=track_artist,
                track_id=track_id,
            )
        return redirect(url_for("entry_page"))

    @app.route("/save-entry", methods=["POST"])
    @login_required
    def save_entry():
        track_name = request.form.get("track_name")
        track_artist = request.form.get("track_artist")
        track_id = request.form.get("track_id")
        mood = request.form.get("mood")

        if not track_name or not track_artist or not track_id or not mood:
            flash("All fields are required!", "error")
            return redirect(url_for("entry_submission_page"))

        entry = {
            "user_id": current_user.id,
            "track_name": track_name,
            "track_artist": track_artist,
            "track_id": track_id,
            "mood": mood,
            "created_at": dt.now(),
        }

        db.entries.insert_one(entry)
        flash("Entry saved successfully!", "success")
        return redirect(url_for("home_page"))

    @app.route("/delete-entry/<entry_id>", methods=["POST"])
    @login_required
    def delete_entry(entry_id):
        try:
            result = db.entries.delete_one(
                {"_id": ObjectId(entry_id), "user_id": current_user.id}
            )
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

        if token:
            song_ids = search_for_song(token, song_name)
            songs = get_songs(token, song_ids)
        else:
            songs = []
        return render_template("search.html", songs=songs)

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            if not username or not password:
                flash("Missing required fields", "error")
                return redirect(url_for("signup"))

            if db.users.find_one({"username": username}):
                flash("User already exists", "error")
                return redirect(url_for("signup"))

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

            if user_data and bcrypt.check_password_hash(
                user_data["password"], password
            ):
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

    @app.route("/search-songs-json", methods=["GET"])
    @login_required
    def search_songs_json():
        token = get_token()
        if not token:
            return jsonify({"error": "Failed to get Spotify access token"}), 500

        song_name = request.args.get("songname", "")
        if not song_name:
            return jsonify({"tracks": []})

        try:
            response = get(
                f"https://api.spotify.com/v1/search?q={song_name}&type=track&limit=12",
                headers=get_auth_headers(token),
            )
            if response.status_code != 200:
                print(f"Search error: {response.content}")
                return jsonify({"error": "Failed to search songs"}), 400

            search_results = response.json()
            tracks = search_results.get("tracks", {}).get("items", [])
            return jsonify({"tracks": tracks})

        except Exception as e:
            print(f"Search error: {str(e)}")
            return jsonify({"error": "Failed to search songs"}), 500

    @app.route("/create-playlist", methods=["POST"])
    @login_required
    def create_playlist():
        try:
            data = request.get_json()
            playlist = {
                "user_id": str(current_user.id),
                "name": data.get(
                    "name",
                    f"Playlist - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                ),
                "description": data.get("description", ""),
                "tracks": data.get("tracks", []),
                "created_at": dt.now(),
            }
            result = db.playlists.insert_one(playlist)

            flash("Playlist created successfully!", "success")
            return (
                jsonify(
                    {
                        "playlist_id": str(result.inserted_id),
                        "message": "Playlist created successfully",
                    }
                ),
                201,
            )

        except Exception as e:
            print(f"Create playlist error: {str(e)}")
            return jsonify({"error": "Failed to create playlist"}), 500

    @app.route("/playlists")
    @login_required
    def playlists_page():
        return render_template("playlists.html")

    @app.route("/recommendations", methods=["GET"])
    @login_required
    def get_mood_recommendations():
        token = get_token()
        if not token:
            return jsonify({"error": "Failed to get Spotify access token"}), 500

        mood = request.args.get("mood", "").lower()
        if not mood:
            return jsonify({"error": "Mood parameter is required"}), 400

        try:
            response = get(
                f"https://api.spotify.com/v1/search?q={mood}&type=track&limit=16",
                headers=get_auth_headers(token),
            )

            if response.status_code != 200:
                print(f"Recommendations error: {response.content}")
                return jsonify({"error": "Failed to get recommendations"}), 400

            tracks = response.json().get("tracks", {}).get("items", [])
            return jsonify({"tracks": tracks})
        except Exception as e:
            print(f"Recommendations error: {str(e)}")
            return jsonify({"error": "Failed to get recommendations"}), 500

    @app.route("/user-playlists", methods=["GET"])
    @login_required
    def get_user_playlists():
        try:
            playlists = list(db.playlists.find({"user_id": str(current_user.id)}))
            for playlist in playlists:
                playlist["_id"] = str(playlist["_id"])
            return jsonify({"playlists": playlists})
        except Exception as e:
            print(f"Get playlists error: {str(e)}")
            return jsonify({"error": "Failed to get playlists"}), 500

    @app.route("/delete-playlist/<playlist_id>", methods=["POST"])
    @login_required
    def delete_playlist(playlist_id):
        try:
            result = db.playlists.delete_one(
                {"_id": ObjectId(playlist_id), "user_id": str(current_user.id)}
            )
            if result.deleted_count > 0:
                flash("Playlist deleted successfully!", "success")
            else:
                flash("Failed to delete playlist or playlist not found.", "error")
        except Exception as e:
            print(f"Error deleting playlist: {e}")
            flash("An error occurred while deleting the playlist.", "error")
        return redirect(url_for("playlists_page"))

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(port=port, debug=(os.getenv("FLASK_ENV") == "development"))
