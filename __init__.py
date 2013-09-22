from flask import Flask

app = Flask(__name__)
from track_app import views
