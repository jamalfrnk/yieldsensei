from flask import Flask

app = Flask(__name__)
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config['TESTING'] = False

@app.route('/')
def hello():
    return "Hello World!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)