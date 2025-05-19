import os
from flask import Flask, render_template, request, redirect
import mysql.connector
from urllib.parse import urlparse

app = Flask(__name__)

def get_db_connection():
    url = urlparse(os.environ.get("MYSQL_URL"))
    return mysql.connector.connect(
        host=url.hostname,
        port=url.port or 3306,
        user=url.username,
        password=url.password,
        database=url.path.lstrip('/')
    )

@app.route('/')
def index():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT name, message, created_at FROM recados ORDER BY id DESC")
    recados = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('index.html', recados=recados)

@app.route('/send', methods=['POST'])
def send():
    try:
        name = request.form['name']
        message = request.form['message']
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("INSERT INTO recados (name, message) VALUES (%s, %s)", (name, message))
        db.commit()
        cursor.close()
        db.close()
        return redirect('/')
    except Exception as e:
        return f"<h1>Error:</h1><pre>{e}</pre>", 500

if __name__ == '__main__':
    app.run(debug=True)
