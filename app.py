import os
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INT NOT NULL,
        target_id INT NOT NULL,
        azione TEXT NOT NULL,
        UNIQUE(user_id, target_id)
    )''')
    # Tabella Messaggi Chat
    c.execute('''CREATE TABLE IF NOT EXISTS messaggi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mittente_id INT NOT NULL,
        destinatario_id INT NOT NULL,
        testo TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db()
    c = conn.cursor()
    # Mostra solo profili che l'utente non ha ancora valutato (like o dislike)
    c.execute('''
        SELECT id, nome, eta, provincia, bio, foto FROM utenti 
        WHERE id != ? AND id NOT IN (SELECT target_id FROM likes WHERE user_id = ?)
    ''', (session['user_id'], session['user_id']))
    profili = [dict(row) for row in c.fetchall()]
    conn.close()

    return render_template_string("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset='UTF-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VibeMate - Lombardia</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f0f13; color: white; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: space-between; min-height: 100vh; }
        header { width: 100%; max-width: 400px; padding: 15px; display: flex; justify-content: space-between; align-items: center; background: #1a1a24; border-bottom: 1px solid #2a2a38; }
        .logo { font-weight: bold; font-size: 20px; color: #ff4757; }
        .user-tag { font-size: 13px; color: #aaa; }
        
        .main-container { width: 100%; max-width: 400px; height: 580px; position: relative; padding: 10px; display: flex; flex-direction: column; justify-content: center; }
        
        .card { width: 100%; height: 100%; background: #1a1a24; border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 8px 20px rgba(0,0,0,0.5); border: 1px solid #2a2a38; }
        .card-img { width: 100%; height: 70%; background-size: cover; background-position: center; }
        .card-info { padding: 15px; }
        .card-info h2 { margin: 0; font-size: 22px; }
        .badge { display: inline-block; background: rgba(255,71,87,0.2); color: #ff4757; border: 1px solid #ff4757; font-size: 11px; padding: 3px 8px; border-radius: 12px; margin-top: 5px; font-weight: bold; }
        .card-info p { margin: 8px 0 0; color: #bbb; font-size: 13px; line-height: 1.4; }
        
        .actions { display: flex; justify-content: space-around; padding: 15px; background: #14141c; }
        .btn { width: 55px; height: 55px; border-radius: 50%; border: none; font-size: 22px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: 0.2s; }
        .dislike { background: #2a2a38; color: #ff4757; }
        .like { background: #ff4757; color: white; box-shadow: 0 4px 15px rgba(255,71,87,0.4); }
        .btn:active { transform: scale(0.9); }

        nav.bottom-bar { width: 100%; max-width: 400px; background: #1a1a24; border-top: 1px solid #2a2a38; display: flex; justify-content: space-around; padding: 12px 0; }
        nav.bottom-bar a { color: #888; text-decoration: none; font-size: 14px; font-weight: bold; text-align: center; }
        nav.bottom-bar a.active { color: #ff4757; }
        
        .no-profiles { text-align: center; color: #888; font-size: 16px; padding: 40px; }
    </style>
</head>
<body>
    <header>
        <div class="logo">VibeMate 🔥</div>
        <div class="user-tag">📍 {{ session.get('user_provincia') }} | {{ session['user_nome'] }}</div>
    </header>

    <div class="main-container">
        <div class="card" id="card">
            <div class="card-img" id="img"></div>
            <div class="card-info">
                <h2 id="name"></h2>
                <span class="badge" id="provincia"></span>
                <p id="bio"></p>
            </div>
            <div class="actions">
                <button class="btn dislike" onclick="swipe('dislike')">❌</button>
                <button class="btn like" onclick="swipe('like')">💚</button>
            </div>
        </div>
        <div id="no-more" class="no-profiles" style="display:none;">
            <h3>Nessun altro profilo in zona! 🎯</h3>
            <p>Torna più tardi per scoprire nuovi profili in Lombardia.</p>
        </div>
    </div>

    <nav class="bottom-bar">
        <a href="/" class="active">🔥 Swipe</a>
        <a href="/matches">💬 Chat & Match</a>
        <a href="/logout">🚪 Esci</a>
    </nav>

    <script>
        let profiles = {{ profili | tojson }};
        let index = 0;

        function renderCard() {
            if (!profiles || index >= profiles.length) {
                document.getElementById('card').style.display = 'none';
                document.getElementById('no-more').style.display = 'block';
                return;
            }
            const p = profiles[index];
            document.getElementById('img').style.backgroundImage = 'url(' + (p.foto || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500') + ')';
            document.getElementById('name').innerText = p.nome + ', ' + p.eta;
            document.getElementById('provincia').innerText = '📍 ' + p.provincia;
            document.getElementById('bio').innerText = p.bio || 'Nessuna biografia.';
        }

        async function swipe(action) {
            if (index >= profiles.length) return;
            const targetId = profiles[index].id;
            
            const res = await fetch('/api/swipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: targetId, action: action })
            });
            const data = await res.json();
            
            if (data.match) {
                alert('🎉 È UN MATCH! Vi siete messi Like a vicenda! Ora puoi scrivergli nella sezione Chat!');
            }

            index++;
            renderCard();
        }

        renderCard();
    </script>
</body>
</html>""", profili=profili)

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
        # Verifica se anche l'altro ha messo like
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
    # Trova utenti con match reciproco
    c.execute('''
        SELECT u.id, u.nome, u.foto, u.provincia FROM utenti u
        JOIN likes l1 ON u.id = l1.target_id AND l1.user_id = ? AND l1.azione = 'like'
        JOIN likes l2 ON u.id = l2.user_id AND l2.target_id = ? AND l2.azione = 'like'
    ''', (user_id, user_id))
    match_list = [dict(row) for row in c.fetchall()]
    conn.close()

    return render_template_string("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset='UTF-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>I tuoi Match - VibeMate</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f0f13; color: white; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: space-between; min-height: 100vh; }
        header { width: 100%; max-width: 400px; padding: 15px; background: #1a1a24; border-bottom: 1px solid #2a2a38; text-align: center; font-weight: bold; font-size: 18px; color: #ff4757; }
        .list-container { width: 100%; max-width: 400px; flex: 1; padding: 15px; overflow-y: auto; }
        .match-item { display: flex; align-items: center; gap: 15px; background: #1a1a24; padding: 12px; border-radius: 12px; margin-bottom: 10px; border: 1px solid #2a2a38; cursor: pointer; text-decoration: none; color: white; }
        .avatar { width: 50px; height: 50px; border-radius: 50%; background-size: cover; background-position: center; }
        .info h4 { margin: 0; font-size: 16px; }
        .info p { margin: 3px 0 0; color: #888; font-size: 12px; }
        nav.bottom-bar { width: 100%; max-width: 400px; background: #1a1a24; border-top: 1px solid #2a2a38; display: flex; justify-content: space-around; padding: 12px 0; }
        nav.bottom-bar a { color: #888; text-decoration: none; font-size: 14px; font-weight: bold; }
        nav.bottom-bar a.active { color: #ff4757; }
    </style>
</head>
<body>
    <header>I Tuoi Match 💬</header>
    <div class="list-container">
        {% if matches %}
            {% for m in matches %}
                <a href="/chat/{{ m.id }}" class="match-item">
                    <div class="avatar" style="background-image: url('{{ m.foto }}')"></div>
                    <div class="info">
                        <h4>{{ m.nome }}</h4>
                        <p>📍 {{ m.provincia }} — Clicca per chattare</p>
                    </div>
                </a>
            {% endfor %}
        {% else %}
            <p style="text-align:center; color:#666; margin-top:50px;">Nessun match ancora.<br>Continua a fare swipe per trovare connessioni!</p>
        {% endif %}
    </div>
    <nav class="bottom-bar">
        <a href="/">🔥 Swipe</a>
        <a href="/matches" class="active">💬 Chat & Match</a>
        <a href="/logout">🚪 Esci</a>
    </nav>
</body>
</html>""", matches=match_list)

@app.route('/chat/<int:target_id>', methods=['GET', 'POST'])
def chat(target_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()

    if request.method == 'POST':
        testo = request.form['testo']
        if testo.strip():
            c.execute('INSERT INTO messaggi (mittente_id, destinatario_id, testo) VALUES (?, ?, ?)', (user_id, target_id, testo))
            conn.commit()
            return redirect(f'/chat/{target_id}')

    c.execute('SELECT nome, foto FROM utenti WHERE id = ?', (target_id,))
    target_user = c.fetchone()

    c.execute('''
        SELECT * FROM messaggi 
        WHERE (mittente_id = ? AND destinatario_id = ?) OR (mittente_id = ? AND destinatario_id = ?)
        ORDER BY timestamp ASC
    ''', (user_id, target_id, target_id, user_id))
    messages = [dict(row) for row in c.fetchall()]
    conn.close()

    return render_template_string("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset='UTF-8'>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat con {{ target.nome }}</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f0f13; color: white; margin: 0; display: flex; flex-direction: column; height: 100vh; align-items: center; }
        header { width: 100%; max-width: 400px; padding: 12px; background: #1a1a24; border-bottom: 1px solid #2a2a38; display: flex; align-items: center; gap: 10px; }
        header a { color: #ff4757; text-decoration: none; font-weight: bold; font-size: 18px; }
        .chat-box { width: 100%; max-width: 400px; flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
        .msg { max-width: 75%; padding: 10px 14px; border-radius: 15px; font-size: 14px; line-height: 1.4; }
        .sent { background: #ff4757; align-self: flex-end; border-bottom-right-radius: 2px; }
        .received { background: #2a2a38; align-self: flex-start; border-bottom-left-radius: 2px; }
        form { width: 100%; max-width: 400px; padding: 10px; background: #1a1a24; display: flex; gap: 8px; border-top: 1px solid #2a2a38; }
        input { flex: 1; padding: 12px; border-radius: 20px; border: 1px solid #333; background: #0f0f13; color: white; outline: none; }
        button { background: #ff4757; color: white; border: none; padding: 0 18px; border-radius: 20px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <header>
        <a href="/matches">‹</a>
        <strong style="font-size: 16px;">{{ target.nome }}</strong>
    </header>
    <div class="chat-box">
        {% for m in messages %}
            <div class="msg {% if m.mittente_id == session['user_id'] %}sent{% else %}received{% endif %}">
                {{ m.testo }}
            </div>
        {% endfor %}
    </div>
    <form method="POST">
        <input type="text" name="testo" placeholder="Scrivi un messaggio..." required autocomplete="off">
        <button type="submit">Invia</button>
    </form>
</body>
</html>""", target=target_user, messages=messages)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = security.generate_password_hash(request.form['password'])
        nome = request.form['nome']
        eta = request.form['eta']
        provincia = request.form['provincia']
        bio = request.form['bio']
        foto = request.form['foto'] or 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=500'

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO utenti (email, password, nome, eta, provincia, bio, foto) VALUES (?, ?, ?, ?, ?, ?, ?)',
                      (email, password, nome, eta, provincia, bio, foto))
            conn.commit()
            conn.close()
            return redirect('/login')
        except sqlite3.IntegrityError:
            conn.close()
            return "Email già registrata! <a href='/login'>Accedi qui</a>"

    return render_template_string("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset='UTF-8'><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Registrati - VibeMate</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f0f13; color: white; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 15px; }
        .box { background: #1a1a24; padding: 25px; border-radius: 20px; width: 100%; max-width: 350px; display: flex; flex-direction: column; gap: 12px; border: 1px solid #2a2a38; }
        h2 { margin: 0 0 10px; color: #ff4757; text-align: center; }
        input, select, textarea, button { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333; background: #0f0f13; color: white; }
        button { background: #ff4757; font-weight: bold; cursor: pointer; border: none; margin-top: 10px; }
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
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
