from flask import Flask, request, jsonify, send_file, render_template
import os
import uuid

try:
    from processing import start_processing, tasks
    PROCESSING_AVAILABLE = True
except Exception:
    # Vercel/serverless runtime cannot host full CV/ML pipeline dependencies.
    PROCESSING_AVAILABLE = False
    tasks = {}

    def start_processing(*args, **kwargs):
        raise RuntimeError('Processing pipeline is unavailable in this deployment.')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.getenv('VERCEL'):
    # Vercel functions can only write to /tmp during invocation.
    UPLOAD_DIR = '/tmp/uploads'
    OUTPUT_DIR = '/tmp/processed'
else:
    UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
    OUTPUT_DIR = os.path.join(BASE_DIR, 'processed')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _allowed_origins():
    raw = os.getenv('ALLOWED_ORIGINS', '*').strip()
    if raw == '*':
        return ['*']
    return [item.strip() for item in raw.split(',') if item.strip()]


ALLOWED_ORIGINS = _allowed_origins()


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '')
    if ALLOWED_ORIGINS == ['*']:
        response.headers['Access-Control-Allow-Origin'] = '*'
    elif origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'

    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response


@app.route('/api/<path:_any>', methods=['OPTIONS'])
def api_options(_any):
    return ('', 204)


@app.route('/')
def index():
    api_base_url = os.getenv('PUBLIC_API_BASE_URL', '').rstrip('/')
    return render_template('index.html', api_base_url=api_base_url)


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'processing_available': PROCESSING_AVAILABLE
    })


@app.route('/api/upload', methods=['POST'])
def upload():
    if not PROCESSING_AVAILABLE:
        return jsonify({'error': 'Video processing is disabled on this deployment.'}), 503

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {'.mp4', '.avi', '.mov', '.mkv'}
    if ext not in allowed:
        return jsonify({'error': f'Invalid format. Allowed: {", ".join(allowed)}'}), 400

    file_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f'{file_id}{ext}')
    output_path = os.path.join(OUTPUT_DIR, f'{file_id}_output.mp4')
    file.save(input_path)

    task_id = start_processing(input_path, output_path, use_stubs=False)

    return jsonify({'task_id': task_id})


@app.route('/api/sample', methods=['POST'])
def process_sample():
    if not PROCESSING_AVAILABLE:
        return jsonify({'error': 'Sample processing is disabled on this deployment.'}), 503

    sample_path = os.path.join(BASE_DIR, 'input_videos', '08fd33_4.mp4')
    if not os.path.exists(sample_path):
        return jsonify({'error': 'Sample video not found'}), 404

    file_id = str(uuid.uuid4())
    output_path = os.path.join(OUTPUT_DIR, f'{file_id}_output.mp4')

    task_id = start_processing(sample_path, output_path, use_stubs=True)

    return jsonify({'task_id': task_id})


@app.route('/api/status/<task_id>')
def status(task_id):
    task = tasks.get(task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)


@app.route('/api/video/<task_id>')
def serve_video(task_id):
    task = tasks.get(task_id)
    if task is None or task.get('status') != 'complete':
        return jsonify({'error': 'Video not ready'}), 404

    output_path = task.get('output_path')
    if output_path and os.path.exists(output_path):
        return send_file(output_path, mimetype='video/mp4')
    return jsonify({'error': 'File not found'}), 404


@app.route('/api/download/<task_id>')
def download(task_id):
    task = tasks.get(task_id)
    if task is None or task.get('status') != 'complete':
        return jsonify({'error': 'Video not ready'}), 404

    output_path = task.get('output_path')
    if output_path and os.path.exists(output_path):
        return send_file(
            output_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name='football_analysis_output.mp4'
        )
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    print("\n  ⚽ Football AI Analyzer running at: http://localhost:8000\n")
    app.run(debug=False, port=8000, threaded=True)
