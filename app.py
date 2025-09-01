from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, JournalEntry
from config import Config
from datetime import datetime, timedelta
import requests
import json

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app

app = create_app()

# Hugging Face Sentiment Analysis API
def analyze_sentiment(text):
    API_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
    headers = {"Authorization": f"Bearer {app.config['HUGGING_FACE_API_KEY']}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text})
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            sentiment_data = result[0]
            # Find the label with highest score
            if len(sentiment_data) > 0:
                highest = max(sentiment_data, key=lambda x: x['score'])
                return highest['label'], highest['score']
        
        return "neutral", 0.5
    except Exception as e:
        print(f"Error in sentiment analysis: {e}")
        return "neutral", 0.5

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get last 7 days of entries for the chart
    seven_days_ago = datetime.now() - timedelta(days=7)
    entries = JournalEntry.query.filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.created_at >= seven_days_ago
    ).order_by(JournalEntry.created_at).all()
    
    # Prepare data for chart
    dates = [entry.created_at.strftime('%Y-%m-%d') for entry in entries]
    scores = [entry.mood_score for entry in entries]
    labels = [entry.mood_label for entry in entries]
    
    return render_template('dashboard.html', 
                          entries=entries, 
                          dates=json.dumps(dates),
                          scores=json.dumps(scores),
                          labels=json.dumps(labels))

@app.route('/add_entry', methods=['POST'])
@login_required
def add_entry():
    content = request.form.get('content')
    if content:
        mood_label, mood_score = analyze_sentiment(content)
        
        new_entry = JournalEntry(
            user_id=current_user.id,
            content=content,
            mood_score=mood_score,
            mood_label=mood_label
        )
        db.session.add(new_entry)
        db.session.commit()
        
        # Check for persistent low mood (3+ days of negative sentiment)
        check_persistent_low_mood(current_user.id)
        
        return jsonify({
            'success': True,
            'mood_label': mood_label,
            'mood_score': mood_score
        })
    
    return jsonify({'success': False, 'error': 'No content provided'})

def check_persistent_low_mood(user_id):
    three_days_ago = datetime.now() - timedelta(days=3)
    recent_entries = JournalEntry.query.filter(
        JournalEntry.user_id == user_id,
        JournalEntry.created_at >= three_days_ago,
        JournalEntry.mood_label.in_(['negative', 'sad'])
    ).all()
    
    if len(recent_entries) >= 3:
        # In a real app, you might send an email notification here
        # For now, we'll just print a message
        print("Alert: User has shown persistent low mood for 3+ days")
        # You could integrate with a notification service here

# Authentication routes would go here (register, login, logout)
# For brevity, I'll include a simplified version

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Simplified registration
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already exists')
        
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:  # In real app, use password hashing!
            login_user(user)
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)