"""
Music journal flask-based web application.
"""

import os
import datetime
from flask import Flask, render_template, request, redirect, url_for
import pymongo
#from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values
import base64
import json
from requests import post, get
import certifi

load_dotenv()  # load environment variables from .env file

def create_app():
    """
    Create and configure the Flask application.
    returns: app: the Flask application object
    """

    app = Flask(__name__)

    # load flask config from env variables
    config = dotenv_values()
    app.config.from_mapping(config)

    mongo_uri = os.getenv("MONGO_URI")
    mongo_dbname = os.getenv("MONGO_DBNAME")

    cxn = pymongo.MongoClient(mongo_uri, tlsCAFile=certifi.where())
    db = cxn[mongo_dbname]

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
    def home():
        """
        Route for the home page.
        Returns:
            rendered template (str): The rendered HTML template.
        """
        return render_template("index.html")

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

    return app

app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5001")
    #FLASK_ENV = os.getenv("FLASK_ENV")

    app.run(port=FLASK_PORT)