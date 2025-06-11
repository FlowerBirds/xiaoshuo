import os
import json

import logging
from flask import Flask, request, jsonify, send_from_directory
import os
import json
from tts_marker import update_chapter, reload_mp3
from flask import make_response


USERNAME = "demo"
PASSWORD = "eabour.163"
from functools import wraps

# Logging configuration
LOG_FILE = os.environ.get('TTS_SERVER_LOG_FILE', 'tts_server.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    logger.warning('Authentication required')
    resp = make_response('Authentication required', 401)
    resp.headers['WWW-Authenticate'] = 'Basic realm="Login Required"'
    return resp


@app.before_request
def require_auth_for_api():
    # 只拦截 API 路径，放行静态资源
    if request.path.startswith('/tts/'):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            logger.info(f'Unauthorized access attempt to {request.path}')
            return authenticate()

PROGRESS_FILE = 'tts_progress.json'


@app.route('/')
def index():
    logger.info('Serving index.html')
    return send_from_directory('static', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    logger.info(f'Serving static file: {filename}')
    return send_from_directory('static', filename)


@app.route('/mp3/<path:filename>')
def serve_mp3(filename):
    logger.info(f'Serving mp3 file: {filename}')
    return send_from_directory('mp3', filename)


@app.route('/tts/save-progress', methods=['POST'])
def save_progress():
    data = request.get_json()
    if not data:
        logger.warning('No data provided to save-progress')
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info('Progress saved successfully')
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f'Error saving progress: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tts/load-progress', methods=['GET'])
def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        logger.warning('Progress file does not exist')
        return jsonify({
            'success': False,
            'error': 'Progress file does not exist',
            'progress': None
        })
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 如果文件为空或内容为空字典/列表，则调用update_chapter()更新
        if not data:
            logger.info('Progress file empty, updating chapter')
            update_chapter()
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f2:
                data = json.load(f2)
        logger.info('Progress loaded successfully')
        return jsonify({'success': True, 'progress': data})
    except Exception as e:
        logger.error(f'Error loading progress: {e}')
        return jsonify({
            'success': False,
            'error': str(e),
            'progress': None
        }), 200


@app.route('/tts/playerlist', methods=['GET'])
def get_playlist():
    books_file = os.path.join('./', 'books.json')
    if not os.path.exists(books_file):
        logger.warning('books.json not found')
        return jsonify({'success': False, 'error': 'books.json not found', 'playlist': None}), 200
    try:
        with open(books_file, 'r', encoding='utf-8') as f:
            playlist = json.load(f)
        logger.info('Playlist loaded successfully')
        return jsonify({'success': True, 'playlist': playlist})
    except Exception as e:
        logger.error(f'Error loading playlist: {e}')
        return jsonify({'success': False, 'error': str(e), 'playlist': None}), 200


@app.route('/tts/update-playerlist', methods=['POST'])
def update_playerlist():
    books_file = os.path.join('./', 'books.json')
    try:
        update_chapter()
        with open(books_file, 'r', encoding='utf-8') as f:
            playlist = json.load(f)
        logger.info('Playerlist updated successfully')
        return jsonify({'success': True, 'playlist': playlist})
    except Exception as e:
        logger.error(f'Error updating playerlist: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/tts/reload-mp3', methods=['POST'])
def reload_mp3_api():
    data = request.get_json()
    txt_path = data.get('txt')
    title = data.get('title')
    if not txt_path or not title:
        logger.warning('Missing txt_path or title in reload-mp3')
        return jsonify({'success': False, 'error': 'Missing txt_path or title'}), 400
    try:
        # 假设 update_chapter 支持传递 txt_path 和 title 参数
        mp3_path = reload_mp3(txt=txt_path, title=title)
        logger.info(f'MP3 reloaded for {title}, path: {mp3_path}')
        return jsonify({'success': True, 'mp3_path': mp3_path})
    except Exception as e:
        logger.error(f'Error reloading mp3: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    debug_mode = os.environ.get('TTS_SERVER_DEBUG', 'False') in ['True', 'true', '1']
    logger.info(f'Starting tts_server... Debug={debug_mode}')
    app.run(debug=debug_mode, port=80, host='0.0.0.0')