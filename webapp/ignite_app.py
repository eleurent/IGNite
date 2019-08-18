import json
from pathlib import Path
from flask import Flask, request, send_from_directory, render_template, redirect, flash, url_for, session, jsonify
from celery import Celery

from ignite import IGNMap
from utils import str_to_point


with open(Path(__file__).parent / "ignite_app_config.json") as f:
    config = json.load(f)

app = Flask(__name__)
app.config['SECRET_KEY'] = config["secret_key"]
celery = Celery(app.name,
                backend='rpc://',
                broker='pyamqp://guest@localhost//')
celery.conf.update(app.config)


@app.route('/')
def home():
    return render_template('index.html',
                           upper_left=session.get("upper_left", ""),
                           lower_right=session.get("lower_right", ""),
                           zoom=session.get("zoom", ""))


@app.route('/generate/', methods=['POST'])
def generate():
    # Get arguments
    upper_left = request.form['upper_left']
    lower_right = request.form['lower_right']
    zoom = request.form['zoom']
    session['upper_left'] = upper_left
    session['lower_right'] = lower_right
    session['zoom'] = zoom

    # Parse arguments
    fail = False
    try:
        upper_left = str_to_point(upper_left)
    except (AttributeError, ValueError) as e:
        flash('Invalid parameter upper_left: {}: {}'.format(upper_left, str(e)))
        fail = True
    try:
        lower_right = str_to_point(lower_right)
    except (AttributeError, ValueError):
        flash('Invalid parameter lower_right: {}'.format(lower_right))
        fail = True
    try:
        zoom = int(zoom)
    except ValueError:
        flash('Invalid parameter zoom: {}'.format(zoom))
        fail = True
    if fail:
        return jsonify({}), 400, {'Location': None}

    task = generate_task.apply_async((upper_left, lower_right, zoom))
    return jsonify({}), 202, {'Location': url_for('taskstatus', task_id=task.id)}


@celery.task(bind=True)
def generate_task(self, upper_left, lower_right, zoom):
    """Background task that runs a long function with progress reports."""
    ignite_config = config.copy()
    ignite_config["--out"] = ignite_config["--out"].format(upper_left, lower_right, zoom)
    self.update_state(state='PROGRESS',
                      meta={'current': 0, 'total': 100,
                            'status': "ignite in progress"})
    ign_map = IGNMap(upper_left, lower_right, zoom, ignite_config)
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': "get/{}".format(Path(ign_map.config["--out"]).with_suffix(".pdf").name)}


@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = generate_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

@app.route('/get/<filename>')
def get_file(filename):
    return send_from_directory('static/generated', filename, as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True)
