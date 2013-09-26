from flask import render_template, request, jsonify, g
import settings
import traceback

from search_app.models import Module, Class, Function
from search_app.models import setProject, getSession
from search_app.views import init_global
from diff import get_code_revisions
from track_app import app


@app.route('/')
@init_global
def index():
    try:
        project_path = settings.PROJECTS[g.project_id]['PROJECT_PATH']
        module_id = request.args.get("module_id")
        class_id = request.args.get("class_id", None)
        function_id = request.args.get("function_id", None)
        module = g.session.query(Module).get(module_id)
        if function_id:
            function_name = g.session.query(Function).get(function_id).name
        else:
            function_name = ""
        if class_id:
            class_name = g.session.query(Class).get(class_id).name
        else:
            class_name = ""

        code_versions = get_code_revisions(project_path, "%s/%s.py" % (module.path, module.name), class_name, function_name)
        result = []
        for c in code_versions:
            result.append(c.as_dict())
    except:
        traceback.print_exc()

    return jsonify({"data": result})
