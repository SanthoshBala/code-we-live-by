from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

def load_title20_data():
    """Load US Code Title 20 data from JSON file"""
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'title20_structure.json')
    with open(data_path, 'r') as f:
        return json.load(f)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/clock')
def clock():
    return render_template('clock.html')

# US Code Browser Routes
@app.route('/uscode')
def uscode_home():
    """Main US Code browser page - redirects to Title 20"""
    data = load_title20_data()
    return render_template('uscode/title.html', title=data['title'], chapters=data['chapters'])

@app.route('/uscode/title/20')
def title20():
    """Display Title 20 - Education overview"""
    data = load_title20_data()
    return render_template('uscode/title.html', title=data['title'], chapters=data['chapters'])

@app.route('/uscode/title/20/chapter/<int:chapter_num>')
def chapter(chapter_num):
    """Display a specific chapter"""
    data = load_title20_data()
    chapter = next((c for c in data['chapters'] if c['number'] == chapter_num), None)

    if not chapter:
        return "Chapter not found", 404

    return render_template('uscode/chapter.html',
                         title=data['title'],
                         chapter=chapter)

@app.route('/uscode/title/20/section/<section_num>')
def section(section_num):
    """Display a specific section"""
    data = load_title20_data()

    # Convert section_num to appropriate type (int or string)
    try:
        section_num = int(section_num)
    except ValueError:
        # Keep as string if it can't be converted to int
        pass

    # Find the section across all chapters
    section = None
    parent_chapter = None
    parent_subchapter = None

    for chapter in data['chapters']:
        # Check sections directly under chapter
        if 'sections' in chapter:
            for sec in chapter['sections']:
                if sec['number'] == section_num:
                    section = sec
                    parent_chapter = chapter
                    break

        # Check sections under subchapters
        if 'subchapters' in chapter:
            for subchapter in chapter['subchapters']:
                if 'sections' in subchapter:
                    for sec in subchapter['sections']:
                        if sec['number'] == section_num:
                            section = sec
                            parent_chapter = chapter
                            parent_subchapter = subchapter
                            break
                if section:
                    break
        if section:
            break

    if not section:
        return "Section not found", 404

    return render_template('uscode/section.html',
                         title=data['title'],
                         chapter=parent_chapter,
                         subchapter=parent_subchapter,
                         section=section)

# API endpoint for JSON data access
@app.route('/api/title/20')
def api_title20():
    """API endpoint to get Title 20 data as JSON"""
    data = load_title20_data()
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
