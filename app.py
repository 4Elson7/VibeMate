import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import werkzeug.security as security

app = Flask(__name__)
app.secret_key = 'vibemate_chiave_segreta_super_sicura'

PROVINCIE_LOMBARDIA = [
    "Bergamo", "Brescia", "Como", "Cremona", "Lecco",
    "Lodi", "Mantova", "Milano", "Monza e Brianza", "Pavia", "Sondrio", "Varese"
]

def get_db():
    conn = sqlite3.connect('tinder.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS utenti (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nome TEXT NOT NULL,
        eta INT NOT NULL,
        provincia TEXT NOT NULL,
        bio TEXT,
        foto TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INT NOT NULL,
        target_id INT NOT NULL,
        azione TEXT NOT NULL,
        UNIQUE(user_id, target_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS messaggi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mittente_id INT NOT NULL,
        destinatario_id INT NOT NULL,
        testo TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

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
        c.execute("SELECT * FROM likes WHERE user_id = ? AND target_id = ? AND azione = 'like'", (target_id, user_id))
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

    return render_template('index.html', is_register=True, provincie=PROVINCIE_LOMBARDIA)

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

    return render_template('index.html', is_login=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
