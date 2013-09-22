from flask import render_template, request, jsonify, g
import settings

from search_app.models import Module, Class, Function
from search_app.models import setProject, getSession
from search_app.views import init_global
from track_app import app


@app.route('/')
@init_global
def index():
    project_path = settings.PROJECTS[g.project_id]['PROJECT_PATH']
    return jsonify({})
