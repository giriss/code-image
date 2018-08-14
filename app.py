from flask import Flask, render_template, request, send_from_directory
from flask.json import dumps as json_dumps
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.formatters import HtmlFormatter
from sass import compile as sass_compile
from uuid import uuid4
import subprocess
import os
import redis

app = Flask(__name__)


DEFAULTS = {
    b'size': b'12',
    b'background': b'rgb(255, 255, 255)',
    b'color': b'rgb(50, 100, 120)',
    b'theme': b'monokai'
}


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

    language = attributes.get(b'language').decode('utf-8')
    lexer = get_lexer_by_name(language)
    highlighted = highlight(attributes.get(b'code').decode('utf-8'), lexer, formatter)

    return render_template(
        'index.jinja2',
        language=language,
        filename=attributes.get(b'filename').decode('utf-8'),
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

    return json_dumps({
        "image_url": "http://localhost:5000/image/%s" % uuid,
        "page_url": "http://localhost:5000/page/%s" % uuid
    })


@app.route('/image/<string:uuid>')
def image(uuid):
    if not os.path.exists('/tmp/highlighter'):
        os.makedirs('/tmp/highlighter')

    out_file = open('/tmp/highlighter/%s.html' % uuid, 'w')
    out_file.write(render(get_attributes_from_redis(uuid)))
    out_file.flush()
    os.fsync(out_file)

    subprocess.call(['wkhtmltoimage', '/tmp/highlighter/%s.html' % uuid, '/tmp/highlighter/%s.png' % uuid])

    resp = send_from_directory('/tmp/highlighter', '%s.png' % uuid, as_attachment=not not request.args.get('download'))

    os.remove('/tmp/highlighter/%s.html' % uuid)
    os.remove('/tmp/highlighter/%s.png' % uuid)

    return resp


@app.route('/page/<string:uuid>')
def page(uuid):
    return render(get_attributes_from_redis(uuid))
