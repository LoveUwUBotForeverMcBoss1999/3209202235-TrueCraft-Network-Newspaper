from flask import Flask, render_template, jsonify, request, abort
from flask_cors import CORS
import os
import re
from datetime import datetime
import markdown
from pathlib import Path

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
NEWSPAPERS_DIR = 'newspapers'

# Enable CORS for all domains and routes
CORS(app)

# Or for more specific CORS configuration, you can use:
# CORS(app, origins=['https://truecraft.top', 'https://www.truecraft.top', 'http://localhost:3000'])


def parse_markdown_metadata(content):
    """Parse YAML-like metadata from markdown files."""
    metadata = {}

    # Split content into metadata and body
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            meta_section = parts[1]
            body = parts[2].strip()

            # Parse metadata
            for line in meta_section.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value

            metadata['content'] = body
        else:
            metadata['content'] = content
    else:
        metadata['content'] = content

    return metadata


def get_all_newspapers():
    """Get all newspaper files and their metadata."""
    newspapers = []
    newspapers_path = Path(NEWSPAPERS_DIR)

    if not newspapers_path.exists():
        return newspapers

    for md_file in newspapers_path.glob('*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata = parse_markdown_metadata(content)

            # Set defaults for missing fields
            newspaper_data = {
                'filename': md_file.stem,
                'title': metadata.get('title', md_file.stem.replace('-', ' ').title()),
                'description': metadata.get('description', 'No description available'),
                'banner_image': metadata.get('banner_image', 'static/logos/logo.png'),
                'author': metadata.get('author', 'TrueCraft Team'),
                'date': metadata.get('date', datetime.now().strftime('%Y-%m-%d')),
                'content': metadata.get('content', '')
            }

            newspapers.append(newspaper_data)

        except Exception as e:
            print(f"Error reading {md_file}: {e}")
            continue

    # Sort by date (newest first)
    newspapers.sort(key=lambda x: x['date'], reverse=True)
    return newspapers


def get_newspaper_by_filename(filename):
    """Get a specific newspaper by filename."""
    newspapers = get_all_newspapers()
    for newspaper in newspapers:
        if newspaper['filename'] == filename:
            return newspaper
    return None


@app.route('/')
def index():
    """Homepage showing latest 5 newspapers."""
    newspapers = get_all_newspapers()[:5]  # Get first 5
    return render_template('index.html',
                           newspapers=newspapers,
                           server_name="TrueCraft Network")


@app.route('/newspapers')
def newspapers_list():
    """All newspapers page with search functionality."""
    search_query = request.args.get('search', '').strip().lower()
    newspapers = get_all_newspapers()

    # Filter newspapers if search query provided
    if search_query:
        filtered_newspapers = []
        for newspaper in newspapers:
            if (search_query in newspaper['title'].lower() or
                    search_query in newspaper['description'].lower() or
                    search_query in newspaper['author'].lower()):
                filtered_newspapers.append(newspaper)
        newspapers = filtered_newspapers

    return render_template('newspapers.html',
                           newspapers=newspapers,
                           search_query=search_query,
                           server_name="TrueCraft Network")


@app.route('/newspaper/<filename>')
def newspaper_detail(filename):
    """Individual newspaper detail page."""
    newspaper = get_newspaper_by_filename(filename)
    if not newspaper:
        abort(404)

    # Convert markdown content to HTML
    html_content = markdown.markdown(newspaper['content'], extensions=['fenced_code'])
    newspaper['html_content'] = html_content

    return render_template('newspaper_detail.html',
                           newspaper=newspaper,
                           server_name="TrueCraft Network")


# API Routes with explicit CORS headers
@app.route('/api/newspapers')
def api_newspapers():
    """API endpoint for top 5 newspapers."""
    newspapers = get_all_newspapers()[:5]
    # Remove content for API response to keep it lightweight
    api_newspapers = []
    for newspaper in newspapers:
        api_newspaper = newspaper.copy()
        del api_newspaper['content']  # Remove full content for list API
        api_newspapers.append(api_newspaper)

    response = jsonify({
        'success': True,
        'newspapers': api_newspapers,
        'count': len(api_newspapers)
    })
    
    # Add explicit CORS headers (flask-cors should handle this, but just in case)
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response


@app.route('/api/newspaper/<filename>')
def api_newspaper_detail(filename):
    """API endpoint for specific newspaper details by filename."""
    newspaper = get_newspaper_by_filename(filename)
    if not newspaper:
        response = jsonify({
            'success': False,
            'error': 'Newspaper not found'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 404

    response = jsonify({
        'success': True,
        'newspaper': {
            'filename': newspaper['filename'],
            'title': newspaper['title'],
            'description': newspaper['description'],
            'banner_image': newspaper['banner_image'],
            'author': newspaper['author'],
            'date': newspaper['date']
        }
    })
    
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response


@app.route('/api/newspaper/<int:index>')
def api_newspaper_by_index(index):
    """API endpoint for specific newspaper details by index (1-based)."""
    newspapers = get_all_newspapers()

    # Convert to 0-based index
    array_index = index - 1

    if array_index < 0 or array_index >= len(newspapers):
        response = jsonify({
            'success': False,
            'error': f'Newspaper index {index} not found. Available range: 1-{len(newspapers)}'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 404

    newspaper = newspapers[array_index]

    response = jsonify({
        'success': True,
        'newspaper': {
            'index': index,
            'filename': newspaper['filename'],
            'title': newspaper['title'],
            'description': newspaper['description'],
            'banner_image': newspaper['banner_image'],
            'author': newspaper['author'],
            'date': newspaper['date']
        }
    })
    
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response


# Handle preflight OPTIONS requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'OK'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response


@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return render_template('404.html', server_name="TrueCraft Network"), 404


if __name__ == '__main__':
    # Create newspapers directory if it doesn't exist
    os.makedirs(NEWSPAPERS_DIR, exist_ok=True)
    app.run(debug=True)
