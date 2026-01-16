from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/clock')
def clock():
    return render_template('clock.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
