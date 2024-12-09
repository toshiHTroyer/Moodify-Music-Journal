"""
Music journal flask-based web application.
"""

import os
import datetime
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import pymongo
import random
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
    def get_mood_features(mood):
        """
        Enhanced audio feature targets for different moods with carefully calibrated values
        based on music psychology research and Spotify's audio features documentation.
        """
        mood_features = {
            "happy": {
                "mood_type": "happy",  # Add mood type for identification
                "target_danceability": 0.7,
                "target_energy": 0.75,
                "target_valence": 0.85,
                "target_tempo": 120,
                "target_mode": 1,
                "min_valence": 0.6,
                "min_energy": 0.5,
                "min_tempo": 85,           # Minimum tempo for happy songs
                "max_instrumentalness": 0.7 # Maximum instrumentalness allowed
            },
            "sad": {
                "target_danceability": 0.35,
                "target_energy": 0.25,
                "target_valence": 0.2,   # Lower valence for melancholic feel
                "target_tempo": 75,      # Slower tempo
                "target_mode": 0,        # Minor key
                "max_valence": 0.4,      # Maximum threshold for positivity
                "max_energy": 0.5        # Maximum energy level
            },
            "angry": {
                "target_danceability": 0.55,
                "target_energy": 0.9,    # High energy
                "target_valence": 0.3,   # Lower valence for intensity
                "target_tempo": 145,     # Fast tempo
                "target_mode": 0,        # Minor key
                "min_energy": 0.7,       # Minimum energy threshold
                "target_loudness": -5    # Louder tracks
            },
            "relaxed": {
                "target_danceability": 0.45,
                "target_energy": 0.35,
                "target_valence": 0.55,  # Moderate valence
                "target_tempo": 85,      # Gentle tempo
                "target_mode": 1,        # Major key
                "max_energy": 0.5,       # Maximum energy threshold
                "target_instrumentalness": 0.3  # Some instrumental presence
            },
            "energetic": {
                "target_danceability": 0.8,
                "target_energy": 0.85,
                "target_valence": 0.75,  # Positive but not necessarily happy
                "target_tempo": 128,     # Dance music tempo
                "target_mode": 1,        # Major key
                "min_energy": 0.7,       # Minimum energy threshold
                "min_danceability": 0.6  # Minimum danceability
            }
        }
        return mood_features.get(mood.lower(), mood_features["happy"])

    def get_mood_search_terms(mood):
        """
        Expanded search terms incorporating genres, decades, and styles
        while maintaining mood consistency
        """
        mood_terms = {
            "happy": [
                # Pop/Contemporary
                "happy upbeat pop",
                "feel good hits",
                "euphoric dance",
                # Rock/Alternative
                "upbeat rock",
                "indie happy",
                "2010 pop"
                "Rihanna Asap"
                # Electronic/Dance
                "hip hop hits"
                "rap happy"
                "rap feelgood"
                # Older Classics
                "classic happy hits",
                "oldies feel good",
                # Global/Cultural
                "latin party",
                "latin party"
                "afrobeats happy",
                "k-pop upbeat",
                "afrobeats vibe"
                "funk happy",
                "reggae positive"
            ],
            "sad": [
                # Pop/Contemporary
                "sad pop ballad",
                "emotional pop",
                "heartbreak songs",
                "breakup lonely"
                "alone crying"
                # Rock/Alternative
                "indie melancholy",
                "emo sad",
                "alt rock emotional",
                # Singer-Songwriter
                "acoustic sad",
                "folk emotional",
                # R&B/Soul
                "soul heartbreak",
                "r&b emotional",
                "blues sad",
                # Genre-Specific
                "sad country",
                "indie folk sad"
            ],
            "angry": [
                # Rock/Metal
                "heavy metal intense",
                "hard rock angry",
                "punk aggressive",
                # Electronic
                "industrial aggressive",
                "electronic rage",
                "dubstep intense",
                # Hip-Hop
                "rap aggressive",
                "hip hop angry",
                "trap intense",
                # Alternative
                "alt metal",
                "grunge angry",
                "hardcore punk",
                # Genre-Mixing
                "metal electronic",
                "rap rock angry",
                "crossover thrash",
                # Experimental
                "experimental aggressive",
                "noise rock",
                "death metal"
            ],
            "relaxed": [
                # Ambient/Electronic
                "ambient peaceful",
                "chillout electronic",
                "downtempo relax",
                # Classical/Piano
                "peaceful piano",
                "classical calm",
                "soft instrumental",
                # Nature/World
                "nature sounds calm",
                "world music relaxing",
                "meditation peaceful",
                # Jazz/Lounge
                "jazz relaxing",
                "lounge chill",
                "bossa nova calm",
                # Modern
                "lo-fi chill",
                "indie ambient",
                "modern classical calm",
                # Acoustic
                "acoustic gentle",
                "folk peaceful",
                "soft guitar"
            ],
            "energetic": [
                # Dance/Electronic
                "edm energy",
                "dance workout",
                "electronic upbeat",
                # Pop/Rock
                "power pop",
                "rock energy",
                "pop workout",
                "hip hop energy",
                "trap workout",
                # Sports/Workout
                "gym motivation",
                "sports anthem",
                "workout hits",
                # Genre-Mixing
                "rock electronic",
                "pop rap energy",
                "crossfit mix",
                # Global
                "latin energy",
                "kpop dance",
                "global workout"
            ]
        }
        # Randomly select 5 diverse terms for broader search
        return random.sample(mood_terms.get(mood.lower(), [""]), min(6, len(mood_terms.get(mood.lower(), [""]))))

    def get_audio_features(token, track_ids):
        """
        Enhanced audio feature retrieval with better error handling
        and larger batch processing
        """
        if not track_ids:
            return []
        
        chunk_size = 100
        all_features = []
        
        for i in range(0, len(track_ids), chunk_size):
            chunk = track_ids[i:i + chunk_size]
            url = f"https://api.spotify.com/v1/audio-features?ids={','.join(chunk)}"
            headers = get_auth_headers(token)
            try:
                response = get(url, headers=headers)
                if response.status_code == 200:
                    features = response.json()
                    if 'audio_features' in features:
                        valid_features = [f for f in features['audio_features'] if f is not None]
                        all_features.extend(valid_features)
                else:
                    print(f"Error status {response.status_code}: {response.content}")
            except Exception as e:
                print(f"Error getting audio features: {e}")
                continue
        
        return all_features

    def calculate_mood_match_score(features, target_features):
        """
        Enhanced scoring with specific filters for happy mood
        """
        if not features:
            return 0
        
        # Special filtering for happy mood
        if 'happy' in target_features.get('mood_type', ''):
            # Filter out very slow tracks (tempo < 85 BPM)
            if features['tempo'] < 70:
                return 0
                
            # Filter out tracks with very low energy
            if features['energy'] < 0.4:
                return 0

        # Core weights for standard features
        weights = {
            'danceability': 0.2,
            'energy': 0.25,
            'valence': 0.3,
            'tempo': 0.15,
            'mode': 0.1
        }
        
        score = 0
        total_weight = 0
        
        # Check thresholds first
        if 'min_valence' in target_features and features['valence'] < target_features['min_valence']:
            return 0
        if 'max_valence' in target_features and features['valence'] > target_features['max_valence']:
            return 0
        if 'min_energy' in target_features and features['energy'] < target_features['min_energy']:
            return 0
        if 'max_energy' in target_features and features['energy'] > target_features['max_energy']:
            return 0
        
        # Calculate core features score
        if 'target_danceability' in target_features:
            score += weights['danceability'] * (1 - abs(features['danceability'] - target_features['target_danceability']))
            total_weight += weights['danceability']
        
        if 'target_energy' in target_features:
            score += weights['energy'] * (1 - abs(features['energy'] - target_features['target_energy']))
            total_weight += weights['energy']
        
        if 'target_valence' in target_features:
            score += weights['valence'] * (1 - abs(features['valence'] - target_features['target_valence']))
            total_weight += weights['valence']
        
        if 'target_tempo' in target_features:
            normalized_tempo = features['tempo'] / 200.0
            normalized_target_tempo = target_features['target_tempo'] / 200.0
            score += weights['tempo'] * (1 - abs(normalized_tempo - normalized_target_tempo))
            total_weight += weights['tempo']
        
        if 'target_mode' in target_features:
            score += weights['mode'] * (1 if features['mode'] == target_features['target_mode'] else 0)
            total_weight += weights['mode']

        return score / total_weight if total_weight > 0 else 0

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
            search_terms = get_mood_search_terms(mood)
            all_tracks = []
            seen_artists = set()  # Track artists to ensure variety
            
            for search_term in search_terms:
                response = get(
                    f"https://api.spotify.com/v1/search?q={search_term}&type=track&limit=30",
                    headers=get_auth_headers(token),
                )
                
                if response.status_code == 200:
                    tracks = response.json().get("tracks", {}).get("items", [])
                    # Filter for artist variety (max 2 songs per artist)
                    for track in tracks:
                        artist_id = track['artists'][0]['id']
                        if artist_id not in seen_artists or sum(1 for t in all_tracks if t['artists'][0]['id'] == artist_id) < 2:
                            all_tracks.append(track)
                            seen_artists.add(artist_id)
            
            random.shuffle(all_tracks)
            
            # Remove duplicates while preserving order
            unique_tracks = []
            seen_ids = set()
            for track in all_tracks:
                if track['id'] not in seen_ids:
                    seen_ids.add(track['id'])
                    unique_tracks.append(track)
            
            if not unique_tracks:
                return jsonify({"tracks": []})

            track_ids = [track['id'] for track in unique_tracks]
            audio_features = get_audio_features(token, track_ids)
            
            if not audio_features:
                random_selection = random.sample(unique_tracks, min(16, len(unique_tracks)))
                return jsonify({"tracks": random_selection})
            
            target_features = get_mood_features(mood)
            track_scores = []
            feature_map = {feature['id']: feature for feature in audio_features if feature}
            
            for track in unique_tracks:
                features = feature_map.get(track['id'])
                if features:
                    score = calculate_mood_match_score(features, target_features)
                    if score > 0:
                        track_scores.append((track, score))
            
            final_tracks = []
            track_scores.sort(key=lambda x: x[1], reverse=True)
            
            total_tracks = len(track_scores)
            top_cutoff = int(total_tracks * 0.5)  # Take top 50% for top tier
            mid_cutoff = int(total_tracks * 0.8)  # Take next 25% for mid tier

            top_third = track_scores[:top_cutoff]               # 50% of tracks
            mid_third = track_scores[top_cutoff:mid_cutoff]     # 30% of tracks
            last_third = track_scores[mid_cutoff:]              # 20% of tracks

            if top_third:
                final_tracks.extend([t for t, _ in random.sample(top_third, min(9, len(top_third)))])  # Take 8 from top
            if mid_third:
                final_tracks.extend([t for t, _ in random.sample(mid_third, min(5, len(mid_third)))])  # Take 4 from middle
            if last_third:
                final_tracks.extend([t for t, _ in random.sample(last_third, min(2, len(last_third)))])  # Take 2 from bottom
            
            
            # Fill remaining slots if needed
            while len(final_tracks) < 14 and track_scores:
                remaining = [t for t, _ in track_scores if t not in final_tracks]
                if not remaining:
                    break
                final_tracks.append(random.choice(remaining))
            
            random.shuffle(final_tracks)  # Final shuffle for variety
            
            return jsonify({"tracks": final_tracks[:16]})
        
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