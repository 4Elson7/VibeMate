import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import werkzeug.security as security
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'vibemate_chiave_segreta_super_sicura'

PROVINCIE_LOMBARDIA = [
    "Bergamo", "Brescia", "Como", "Cremona", "Lecco",
    "Lodi", "Mantova", "Milano", "Monza e Brianza", "Pavia", "Sondrio", "Varese"
]

def get_db():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        return conn
    conn = sqlite3.connect('tinder.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Tabella Utenti
    c.execute('''CREATE TABLE IF NOT EXISTS utenti (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nome TEXT NOT NULL,
        eta INT NOT NULL,
        provincia TEXT NOT NULL,
        bio TEXT,
        foto TEXT
    )''')
    
    # Tabella Like / Swipes
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        target_id INT NOT NULL,
        azione TEXT NOT NULL,
        UNIQUE(user_id, target_id)
    )''')
    
    # Tabella Messaggi Chat
    c.execute('''CREATE TABLE IF NOT EXISTS messaggi (
        id SERIAL PRIMARY KEY,
        mittente_id INT NOT NULL,
        destinatario_id INT NOT NULL,
        testo TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# Inizializza il database in modo sicuro all'avvio dell'applicazione
with app.app_context():
    init_db()

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, nome, eta, provincia, bio, foto FROM utenti
        WHERE id != ? AND id NOT IN (SELECT target_id FROM likes WHERE user_id = ?)
    ''', (session['user_id'], session['user_id']))
    profili = [dict(row) for row in c.fetchall()]
    conn.close()

    return render_template('index.html', profili=profili)

@app.route('/api/swipe', methods=['POST'])
def api_swipe():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_id = session['user_id']
    target_id = data['target_id']
    action = data['action']

    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO likes (user_id, target_id, azione) VALUES (?, ?, ?)', (user_id, target_id, action))
    conn.commit()

    is_match = False
    if action == 'like':
        c.execute('SELECT * FROM likes WHERE user_id = ? AND target_id = ? AND azione = "like"', (target_id, user_id))
        if c.fetchone():
            is_match = True

    conn.close()
    return jsonify({'success': True, 'match': is_match})

@app.route('/matches')
def matches():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.nome, u.foto, u.provincia FROM utenti u
        JOIN likes l1 ON u.id = l1.target_id AND l1.user_id = ? AND l1.azione = 'like'
        JOIN likes l2 ON u.id = l2.user_id AND l2.target_id = ? AND l2.azione = 'like'
    ''', (user_id, user_id))
    match_list = [dict(row) for row in c.fetchall()]
    conn.close()

    return "Sezione Match in arrivo!"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = security.generate_password_hash(request.form['password'])
        nome = request.form['nome']
        eta = request.form['eta']
        provincia = request.form['provincia']
        bio = request.form.get('bio', '')
        foto = request.form.get('foto', '')

        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('INSERT INTO utenti (email, password, nome, eta, provincia, bio, foto) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (email, password, nome, eta, provincia, bio, foto))
            conn.commit()
            conn.close()
            return redirect('/login')
        except Exception as e:
            return f"Errore durante la registrazione (Email già in uso?): {e} <a href='/register'>Riprova</a>"

    return render_template_string("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset='UTF-8'><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Registrazione - VibeMate</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f0f13; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 15px; }
        .box { background: #1a1a24; padding: 25px; border-radius: 20px; width: 100%; max-width: 350px; display: flex; flex-direction: column; gap: 12px; border: 1px solid #2a2a38; }
        h2 { margin: 0 0 10px; color: #ff4757; text-align: center; }
        input, select, textarea, button { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333; background: #0f0f13; color: white; font-size: 14px; }
        textarea { resize: vertical; height: 80px; }
        button { background: #ff4757; font-weight: bold; cursor: pointer; border: none; margin-top: 5px; }
        a { color: #ff4757; text-decoration: none; text-align: center; display: block; margin-top: 10px; font-size: 13px; }
    </style>
</head>
<body>
    <form class='box' method='POST'>
        <h2>VibeMate Lombardia 🔥</h2>
        <input type='email' name='email' placeholder='Email' required>
        <input type='password' name='password' placeholder='Password' required>
        <input type='text' name='nome' placeholder='Nome' required>
        <input type='number' name='eta' placeholder='Età' required>
        <select name='provincia' required>
            <option value='' disabled selected>Seleziona Provincia (Lombardia)</option>
            {% for prov in provincie %}
                <option value='{{ prov }}'>{{ prov }}</option>
            {% endfor %}
        </select>
        <textarea name='bio' placeholder='La tua biografia'></textarea>
        <input type='text' name='foto' placeholder='Link URL foto profilo (opzionale)'>
        <button type='submit'>Crea Account</button>
        <a href='/login'>Hai già un account? Accedi</a>
    </form>
</body>
</html>""", provincie=PROVINCIE_LOMBARDIA)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM utenti WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()

        if user and security.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_nome'] = user['nome']
            session['user_provincia'] = user['provincia']
            return redirect('/')
        else:
            return "Credenziali errate! <a href='/login'>Riprova</a>"

    return render_template_string("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset='UTF-8'><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login - VibeMate</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f0f13; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; padding: 15px; }
        .box { background: #1a1a24; padding: 25px; border-radius: 20px; width: 100%; max-width: 330px; display: flex; flex-direction: column; gap: 12px; border: 1px solid #2a2a38; }
        h2 { margin: 0 0 10px; color: #ff4757; text-align: center; }
        input, button { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333; background: #0f0f13; color: white; }
        button { background: #ff4757; font-weight: bold; cursor: pointer; border: none; margin-top: 10px; }
        a { color: #ff4757; text-decoration: none; text-align: center; display: block; margin-top: 10px; font-size: 13px; }
    </style>
</head>
<body>
    <form class='box' method='POST'>
        <h2>VibeMate 🔥</h2>
        <input type='email' name='email' placeholder='Email' required>
        <input type='password' name='password' placeholder='Password' required>
        <button type='submit'>Accedi</button>
        <a href='/register'>Non hai un account? Registrati</a>
    </form>
</body>
</html>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
