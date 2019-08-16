import json
from pathlib import Path
from flask import Flask, request, send_from_directory, render_template, redirect, flash, url_for, session, jsonify
import random
import time
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
    print(str(Path(ign_map.config["--out"]).with_suffix(".pdf")))
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': str(Path(ign_map.config["--out"]).with_suffix(".pdf"))}


@celery.task(bind=True)
def long_task(self):
    """Background task that runs a long function with progress reports."""
    verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
    adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
    noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
    message = ''
    total = random.randint(10, 20)
    for i in range(total):
        if not message or random.random() < 0.25:
            message = '{0} {1} {2}...'.format(random.choice(verb),
                                              random.choice(adjective),
                                              random.choice(noun))
        self.update_state(state='PROGRESS',
                          meta={'current': i, 'total': total,
                                'status': message})
        time.sleep(0.2)
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': 42}


@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}


@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
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


if __name__ == "__main__":
    app.run(debug=True)
