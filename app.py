from flask import Flask, render_template, request, send_from_directory
from flask.json import dumps as json_dumps
from pygments import highlight
from pygments.lexers import PythonLexer, get_lexer_by_name, get_lexer_for_filename
from pygments.formatters import HtmlFormatter
from sass import compile as sass_compile
from uuid import uuid4
import subprocess
import os

app = Flask(__name__)

@app.route('/highlight', methods=['POST'])
def highlight_code():
    json = request.get_json()
    size = json.get('size', '12')
    background = json.get('background', 'rgb(255, 255, 255)')
    color = json.get('color', 'rgb(30, 30, 80)')
    code = json.get('code')
    language = json.get('language')
    filename = json.get('filename')
    theme = json.get('theme')

    sass_variables = '$main-size: %spx\n' % size
    sass_variables += '$body-color: %s\n' % background
    sass_variables += '$back-color: %s\n' % color
    sass_file = sass_variables + open('assets/styles/main.sass', 'r').read()
    css_output = sass_compile(string=sass_file, indented=True)

    formatter = HtmlFormatter(style='monokai')
    style = css_output + formatter.get_style_defs()

    lexer = get_lexer_for_filename(filename)
    highlighted = highlight(code, lexer, formatter)

    if not os.path.exists('/tmp/highlighter'):
        os.makedirs('/tmp/highlighter')
    uuid = uuid4()
    os.makedirs('/tmp/highlighter/%s' % uuid)

    out_file = open('/tmp/highlighter/%s/index.html' % uuid, 'w')
    out_file.write(render_template('index.jinja2', language=language, highlighted=highlighted, style=style))
    out_file.flush()
    os.fsync(out_file)

    subprocess.call(['wkhtmltoimage', '/tmp/highlighter/%s/index.html' % uuid, '/tmp/highlighter/%s/index.png' % uuid])

    resp = {"url": "http://localhost:5000/image/%s" % uuid}

    return json_dumps(resp)

@app.route('/image/<string:uuid>')
def image(uuid):
    return send_from_directory('/tmp/highlighter/%s' % uuid, 'index.png', as_attachment=not not request.args.get('download'))
