from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return f"Hello! PORT={os.getenv('PORT', 'not set')}"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
