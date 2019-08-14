from pathlib import Path
from flask import Flask, request, send_from_directory, render_template, redirect, flash, url_for, session

from ignite import IGNMap
from utils import str_to_point

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top-secret!'


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_template('index.html',
                               upper_left=session.get("upper_left", ""),
                               lower_right=session.get("lower_right", ""),
                               zoom=session.get("zoom", ""))

    upper_left = request.form['upper_left']
    lower_right = request.form['lower_right']
    zoom = request.form['zoom']
    session['upper_left'] = upper_left
    session['lower_right'] = lower_right
    session['zoom'] = zoom
    return ignite(upper_left, lower_right, zoom)


def ignite(upper_left, lower_right, zoom):
    config = {
        "--processes": 4,
        "--out": "app/generated/out",
        "--cache-folder": "cache",
        "--no-caching": None
    }
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
        return redirect(url_for('home'))

    # Generate map
    ign_map = IGNMap(upper_left, lower_right, zoom, config)
    pdf_path = Path(ign_map.config["--out"]).with_suffix(".pdf")
    return send_from_directory(directory=pdf_path.parent.relative_to(pdf_path.parent.parts[0]),
                               filename=pdf_path.name,
                               mimetype='application/pdf')


if __name__ == "__main__":
    app.run(debug=True)
