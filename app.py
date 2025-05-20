import os
import mysql.connector
import re
from flask import Flask, render_template, request, redirect, flash
from urllib.parse import urlparse
from datetime import datetime
from zoneinfo import ZoneInfo
from babel.dates import format_datetime
from bleach import clean
from markupsafe import escape

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
os.environ["MYSQL_URL"] = "mysql://root:negativo@localhost:3306/mural"

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
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    recados = []
    for nome, recado, data in rows:
        if data.tzinfo is None:
            data = data.replace(tzinfo=ZoneInfo("UTC"))
        data_br = data.astimezone(ZoneInfo("America/Sao_Paulo"))
        data_formatada = format_datetime(data_br, "d 'de' MMMM 'de' y 'às' HH:mm", locale='pt_BR')
        recados.append((nome, recado, data_formatada))

    return render_template('index.html', recados=recados)

@app.route('/send', methods=['POST'])
def send():
    try:
        # Get form data safely
        name = request.form.get('name', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validate inputs
        try:
            name = validate_name(name)
            message = validate_message(message)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect('/')
        
        # Database operations
        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO recados (name, message) VALUES (%s, %s)",
                (name, message)
            )
            db.commit()
            flash('Recado enviado com sucesso!', 'success')
            return redirect('/')
            
        except mysql.connector.Error as err:
            flash(f"Erro no banco de dados: {err.msg}", 'error')
            return redirect('/')
            
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'db' in locals(): db.close()
            
    except re.error as regex_err:
        flash("Erro no sistema: configuração inválida", 'error')
        app.logger.error(f"Regex error: {regex_err}")
        return redirect('/')
        
    except Exception as e:
        flash(f"Erro inesperado: {str(e)}", 'error')
        app.logger.error(f"Unexpected error: {str(e)}")
        return redirect('/')

def validate_name(name):
    """Validate and sanitize the name field"""
    if not name or len(name.strip()) == 0:
        raise ValueError("O nome não pode estar vazio")
    
    if len(name) > 100:
        raise ValueError("O nome é muito longo (máximo 100 caracteres)")
    
    if not re.match(r'^[\w\s\'-]+$', name, re.UNICODE):
        raise ValueError("O nome contém caracteres inválidos")
    
    return clean(name.strip(), tags=[], attributes={})

def validate_message(message):
    """Validate and sanitize the message field"""
    if not message or len(message.strip()) == 0:
        raise ValueError("A mensagem não pode estar vazia")
    
    if len(message) > 2000:
        raise ValueError("A mensagem é muito longa (máximo 2000 caracteres)")

    forbidden_patterns = [
        r"<script.*?>", r"</script>",
        r"on[a-z]+\s*=",
        r"javascript:", 
        r"vbscript:",
        r"expression\s*\(",
        
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bALTER\b",
        r"\bUNION\b",
        r"\bSELECT\b.*\bFROM\b",
        r"--\s*$",
        r";\s*$",
        r"'\s*OR\s*['1]='1",
        r"\bEXEC\b",
        r"\bXP_",
        r"\bWAITFOR\b",
        r"\bSHUTDOWN\b"
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            raise ValueError("Mensagem contém conteúdo não permitido")

    allowed_tags = ['b', 'i', 'em', 'strong', 'p', 'br']
    return clean(message.strip(), tags=allowed_tags, attributes={}, strip=True)

if __name__ == '__main__':
    app.run(debug=True)