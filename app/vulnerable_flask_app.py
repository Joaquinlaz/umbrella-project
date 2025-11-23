from flask import Flask, request, render_template_string, session, redirect, url_for, Response
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
import sqlite3
import os
import hashlib
# Monitorización
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter

app = Flask(__name__)
# Generamos una clave secreta aleatoria para firmar los tokens CSRF y la sesión
app.secret_key = os.urandom(24)

# --- 1. CONFIGURACIÓN DE SEGURIDAD (Arregla CSP, Clickjacking, X-Content-Type) ---
# Definimos qué scripts y estilos externos permitimos (CSP)
csp = {
    'default-src': '\'self\'',
    'script-src': [
        '\'self\'',
        'https://maxcdn.bootstrapcdn.com',
        'https://code.jquery.com',
        'https://cdnjs.cloudflare.com'
    ],
    'style-src': [
        '\'self\'',
        'https://maxcdn.bootstrapcdn.com'
    ]
}

# force_https=False es CRUCIAL para Docker local sin SSL.
# Esto inyecta automáticamente las cabeceras X-Frame-Options, X-Content-Type-Options, etc.
Talisman(app, content_security_policy=csp, force_https=False)

# --- 2. PROTECCIÓN CSRF (Arregla "Ausencia de Tokens Anti-CSRF") ---
csrf = CSRFProtect(app)

# --- 3. MÉTRICAS DE NEGOCIO (Login) ---
LOGIN_FAILURES = Counter('app_login_failures_total', 'Total de intentos de login fallidos')
LOGIN_SUCCESS = Counter('app_login_success_total', 'Total de logins exitosos')

def get_db_connection():
    conn = sqlite3.connect('example.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
            <title>Welcome</title>
        </head>
        <body>
            <div class="container">
                <h1 class="mt-5">Welcome to the Secure Application!</h1>
                <p class="lead">This is the home page. Please <a href="/login">login</a>.</p>
            </div>
        </body>
        </html>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        # --- ARREGLO INYECCIÓN SQL (Critico) ---
        # Se elimina la concatenación de strings y el chequeo inseguro "OR".
        # Se usa la parametrización nativa de SQLite (?)
        query = "SELECT * FROM users WHERE username = ? AND password = ?"
        hashed_password = hash_password(password)
        
        # Ejecutamos la query de forma segura
        user = conn.execute(query, (username, hashed_password)).fetchone()
        conn.close()

        if user:
            LOGIN_SUCCESS.inc()
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            LOGIN_FAILURES.inc()
            return render_login_page(error="Invalid credentials!")

    # GET request
    return render_login_page()

def render_login_page(error=None):
    error_html = f'<div class="alert alert-danger" role="alert">{error}</div>' if error else ''
    # Flask-WTF requiere que pasemos csrf_token() al template, pero al usar render_template_string
    # dentro del contexto de Flask, jinja2 lo resuelve automáticamente si CSRFProtect está activo.
    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
            <title>Login</title>
        </head>
        <body>
            <div class="container">
                <h1 class="mt-5">Login</h1>
                ''' + error_html + '''
                <form method="post">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                    
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                </form>
            </div>
        </body>
        </html>
    ''')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    comments = conn.execute(
        "SELECT comment FROM comments WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
            <title>Dashboard</title>
        </head>
        <body>
            <div class="container">
                <h1 class="mt-5">Welcome, user {{ user_id }}!</h1>
                <form action="/submit_comment" method="post">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                    
                    <div class="form-group">
                        <label for="comment">Comment</label>
                        <textarea class="form-control" id="comment" name="comment" rows="3"></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Submit Comment</button>
                </form>
                <h2 class="mt-5">Your Comments</h2>
                <ul class="list-group">
                    {% for comment in comments %}
                        <li class="list-group-item">{{ comment['comment'] }}</li>
                    {% endfor %}
                </ul>
            </div>
        </body>
        </html>
    ''', user_id=user_id, comments=comments)

# --- ARREGLO FUGA DE VERSIÓN (Server Header Leak) ---
@app.after_request
def remove_server_header(response):
    # Eliminamos la cabecera 'Server' para que no diga "Werkzeug/2.0.3 Python/3.9"
    response.headers.pop('Server', None)
    return response

@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    comment = request.form['comment']
    user_id = session['user_id']

    conn = get_db_connection()
    # Usamos parámetros seguros aquí también por si acaso
    conn.execute(
        "INSERT INTO comments (user_id, comment) VALUES (?, ?)", (user_id, comment))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    return render_template_string('''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
            <title>Admin Panel</title>
        </head>
        <body>
            <div class="container">
                <h1 class="mt-5">Welcome to the admin panel!</h1>
            </div>
        </body>
        </html>
    ''')

# --- RUTA PARA MONITORIZACIÓN ---
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    if not os.path.exists('example.db'):
        import create_db
    # Mantenemos debug=True para desarrollo, pero en prod debería ser False
    app.run(debug=True, host='0.0.0.0')
