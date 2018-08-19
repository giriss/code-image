from flask import Flask, render_template, request, send_from_directory
from flask.json import jsonify
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from sass import compile as sass_compile
from uuid import uuid4
import subprocess
import os
import redis

app = Flask(__name__)


DEFAULTS = {
    b'size': b'12',
    b'background': b'rgb(255, 255, 255)',
    b'color': b'rgb(10, 50, 70)',
    b'theme': b'monokai'
}

TMP_DIR = '/tmp/highlighter'


def redis_conn():
    return redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost'))


def get_attributes_from_redis(uuid):
    return redis_conn().hgetall(uuid)


def render(attributes):
    sass_variables = '$main-size: %spx\n' % attributes.get(b'size', DEFAULTS[b'size']).decode('utf-8')
    sass_variables += '$body-color: %s\n' % attributes.get(b'background', DEFAULTS[b'background']).decode('utf-8')
    sass_variables += '$back-color: %s\n' % attributes.get(b'color', DEFAULTS[b'color']).decode('utf-8')
    sass_file = sass_variables + open('assets/styles/main.sass', 'r').read()
    css_output = sass_compile(string=sass_file, indented=True)

    formatter = HtmlFormatter(style=attributes.get(b'theme', DEFAULTS[b'theme']).decode('utf-8'))
    style = css_output + formatter.get_style_defs()

    language = attributes.get(b'language')
    language = language and language.decode('utf-8')
    filename = attributes.get(b'filename')
    filename = filename and filename.decode('utf-8')

    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        lexer = get_lexer_for_filename(filename)

    highlighted = highlight(attributes.get(b'code').decode('utf-8'), lexer, formatter)

    return render_template(
        'index.jinja2',
        language=language or lexer.name,
        filename=filename,
        highlighted=highlighted,
        style=style
    )


@app.route('/highlight', methods=['POST'])
def highlight_code():
    json = request.get_json()
    language = json.get('language')
    filename = json.get('filename')
    theme = json.get('theme')
    size = json.get('size')
    background = json.get('background')
    color = json.get('color')

    redis_instance = redis_conn()

    attributes = {
        'code': json.get('code')
    }
    if size:
        attributes['size'] = size
    if background:
        attributes['background'] = background
    if color:
        attributes['color'] = color
    if language:
        attributes['language'] = language
    if filename:
        attributes['filename'] = filename
    if theme:
        attributes['theme'] = theme

    uuid = uuid4()
    redis_instance.hmset(uuid, attributes)
    redis_instance.expire(uuid, 600) # expire in 10 minutes

    return jsonify({
        "image_url": "%simage/%s" % (request.host_url, uuid),
        "page_url": "%spage/%s" % (request.host_url, uuid)
    })


@app.route('/image/<string:uuid>')
def image(uuid):
    attributes = get_attributes_from_redis(uuid)
    if attributes == {}:
        return 'Not found or expired', 404

    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)

    out_file = open('%s/%s.html' % (TMP_DIR, uuid), 'w')
    out_file.write(render(attributes))
    out_file.flush()
    os.fsync(out_file)

    command = 'wkhtmltoimage'
    if os.path.exists('/app/bin/%s' % command):
        command = '/app/bin/%s' % command

    subprocess.call([command, '%s/%s.html' % (TMP_DIR, uuid), '%s/%s.png' % (TMP_DIR, uuid)])

    resp = send_from_directory(TMP_DIR, '%s.png' % uuid, as_attachment=not not request.args.get('download'))

    os.remove('%s/%s.html' % (TMP_DIR, uuid))
    os.remove('%s/%s.png' % (TMP_DIR, uuid))

    return resp


@app.route('/page/<string:uuid>')
def page(uuid):
    attributes = get_attributes_from_redis(uuid)
    if attributes == {}:
        return 'Not found or expired', 404
    else:
        return render(attributes)
