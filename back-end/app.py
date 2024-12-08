"""
Music journal flask-based web application.
"""

import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import pymongo
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv, dotenv_values
import base64
import json
from requests import post, get
import certifi
from bson import ObjectId

load_dotenv()  # load environment variables from .env file


def create_app():
    """
    Create and configure the Flask application.
    returns: app: the Flask application object
    """

    app = Flask(__name__)
    bcrypt = Bcrypt(app)
    jwt = JWTManager(app)

    # load flask config from env variables
    config = dotenv_values()
    app.config.from_mapping(config)

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "your_jwt_secret_key")

    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
    db = cxn[os.getenv("MONGO_DBNAME")]

    try:
        cxn.admin.command("ping")
        print(" *", "Connected to MongoDB!")
    except Exception as e:
        print(" * MongoDB connection error:", e)

    cli_id = os.getenv("CLIENT_ID")
    cli_secret = os.getenv("CLIENT_SECRET")

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
        json_res = json.loads(res.content)["tracks"]["items"]

        if len(json_res) == 0:
            return None
        
        return ','.join([song["id"] for song in json_res])

    def get_songs(token, song_ids):
        url = f"https://api.spotify.com/v1/tracks?ids={song_ids}"
        print(url)
        headers = get_auth_headers(token)

        res = get(url, headers=headers)
        json_res = json.loads(res.content)["tracks"]

        return json_res

    @app.route("/")
    def login_page():
        """
        Route for the home page.
        Returns:
            rendered template (str): The rendered HTML template.
        """
        return render_template("login.html")


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

    @app.route("/search-songs")
    def search():
        # get spotify access token
        token = get_token()

        # get search query from user
        song_name = request.form["songname"]

        # search for song + get ids
        song_ids = search_for_song(token, song_name)
        songs = get_songs(token, song_ids)

        return render_template("search.html", songs=songs)

    # Authentication routes

    @app.route("/api/auth/signup", methods=["POST"])
    def signup():
        """
        Handles user signup.
        Expects JSON payload: { "username": "example", "email": "example@mail.com", "password": "password123" }
        """
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if not username or not email or not password:
            return jsonify({"error": "Missing required fields"}), 400

        # Check if user already exists
        if db.users.find_one({"email": email}):
            return jsonify({"error": "User already exists"}), 400

        # Hash the password and save the user
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        user = {"username": username, "email": email, "password": hashed_password}
        db.users.insert_one(user)

        return jsonify({"message": "User registered successfully"}), 201

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        """
        Handles user login.
        Expects JSON payload: { "email": "example@mail.com", "password": "password123" }
        """
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        user = db.users.find_one({"email": email})
        if not user or not bcrypt.check_password_hash(user["password"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate a JWT token
        token = create_access_token(identity=str(user["_id"]))
        return jsonify({"token": token}), 200

    @app.route("/api/auth/logout", methods=["POST"])
    @jwt_required()
    def logout():
        """
        Handles user logout (optional for stateless JWT).
        """
        return jsonify({"message": "Logged out"}), 200

    @app.route("/api/home", methods=["GET"])
    @jwt_required()
    def user_home():
        """
        Home page that displays user profile and journal data.
        """
        user_id = get_jwt_identity()
        user = db.users.find_one({"_id": ObjectId(user_id)})  # 修改为 ObjectId

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Example profile and journal data
        profile = {
            "username": user["username"],
            "email": user["email"],
            "journal_graph": {"entries": 10, "sentiments": [3, 4, 5, 3]},
            "playlists": ["Rock Classics", "Jazz Vibes", "Top Hits"]
        }

        return jsonify(profile), 200

    return app


app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    app.run(port=FLASK_PORT, debug=True)  # Enable debug mode
