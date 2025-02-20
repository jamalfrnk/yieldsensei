import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import asyncio
from services.technical_analysis import get_signal_analysis
from services.coingecko_service import get_token_price, get_token_market_data
import logging
from datetime import datetime, timedelta
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from models import db, Quiz, Question, UserProgress, User

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Default data for the dashboard
DEFAULT_DATA = {
    'price': 0.0,
    'price_change': 0.0,
    'signal_strength': 0,
    'signal_description': 'Enter a token to analyze',
    'trend_score': 50,
    'trend_direction': 'Neutral ⚖️',
    'market_status': 'Neutral ⚖️',
    'rsi': 50,
    'support_1': 0.0,
    'support_2': 0.0,
    'resistance_1': 0.0,
    'resistance_2': 0.0,
    'dca_recommendation': 'Enter a token to get DCA recommendations',
    'chart_data': {
        'labels': [],
        'datasets': []
    }
}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Security headers
Talisman(app, 
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
        'style-src': ["'self'", "'unsafe-inline'", 'cdn.jsdelivr.net'],
        'img-src': ["'self'", 'data:', 'cdn.jsdelivr.net'],
        'font-src': ["'self'", 'cdn.jsdelivr.net']
    },
    force_https=False  # Disable HTTPS for local development
)

# Enable compression
Compress(app)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

# Register template filters
@app.template_filter('price_color')
def price_color_filter(value):
    """Return CSS class based on price change value."""
    try:
        value = float(value)
        return 'text-green-500' if value >= 0 else 'text-red-500'
    except (ValueError, TypeError):
        return 'text-gray-500'

@app.route('/')
@limiter.exempt
async def index():
    """Render the main dashboard."""
    return render_template('dashboard.html', **DEFAULT_DATA)

@app.route('/search')
@limiter.limit("20 per minute")
async def search():
    """Handle token search and analysis."""
    token = request.args.get('token', 'bitcoin').lower()
    try:
        # Get market data
        price_data = await get_token_price(token)
        signal_data = await get_signal_analysis(token)

        # Calculate trend score (0-100)
        trend_score = min(100, max(0, float(signal_data['signal_strength'])))

        template_data = {
            'price': float(price_data['usd']),
            'price_change': float(price_data['usd_24h_change']),
            'signal_strength': float(signal_data['signal_strength']),
            'signal_description': signal_data['signal'],
            'trend_score': trend_score,
            'trend_direction': signal_data['trend_direction'],
            'market_status': get_market_status(float(signal_data['rsi'])),
            'rsi': float(signal_data['rsi']),
            'support_1': float(signal_data['support_1'].replace('$', '').replace(',', '')),
            'support_2': float(signal_data['support_2'].replace('$', '').replace(',', '')),
            'resistance_1': float(signal_data['resistance_1'].replace('$', '').replace(',', '')),
            'resistance_2': float(signal_data['resistance_2'].replace('$', '').replace(',', '')),
            'dca_recommendation': signal_data['dca_recommendation'],
            'chart_data': {
                'labels': [],
                'datasets': []
            }
        }

        return render_template('dashboard.html', **template_data)
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}")
        return render_template('dashboard.html', error=str(e), **DEFAULT_DATA)

def get_market_status(rsi):
    """Determine market status based on RSI."""
    if rsi >= 70:
        return "Overbought 🔴"
    elif rsi <= 30:
        return "Oversold 🟢"
    else:
        return "Neutral ⚖️"


@app.route('/quizzes')
def quizzes():
    """Display available quizzes and leaderboard."""
    available_quizzes = Quiz.query.all()
    leaderboard = UserProgress.get_leaderboard(limit=10)
    return render_template('quiz.html', quizzes=available_quizzes, leaderboard=leaderboard)

@app.route('/quiz/<int:quiz_id>')
def start_quiz(quiz_id):
    """Start or continue a quiz."""
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return render_template('quiz_questions.html', quiz=quiz, questions=questions)

@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    """Handle quiz submission and scoring."""
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    score = 0
    total_questions = len(questions)

    for question in questions:
        user_answer = request.form.get(f'q{question.id}')
        if user_answer == question.correct_answer:
            score += 1

    # Calculate percentage score
    percentage_score = (score / total_questions) * 100

    # Update user progress
    progress = UserProgress(
        user_id=1,  # Hardcoded for now, replace with current_user.id when auth is added
        quiz_id=quiz_id,
        score=percentage_score,
        completed=True,
        attempts=1
    )
    db.session.add(progress)

    # Update user points
    points_earned = int((quiz.points_reward * percentage_score) / 100)
    user = User.query.get(1)  # Hardcoded for now
    user.points += points_earned

    db.session.commit()

    return render_template('quiz_results.html', 
                         score=score,
                         total=total_questions,
                         percentage=percentage_score,
                         points_earned=points_earned)

# Initialize database
with app.app_context():
    db.create_all()

    # Create default user if none exists
    if not User.query.first():
        default_user = User(
            username="default_user",
            email="default@example.com",
            points=0
        )
        db.session.add(default_user)
        db.session.commit()

    # Add sample quiz data if none exists
    if not Quiz.query.first():
        sample_quiz = Quiz(
            title="Crypto Basics 101",
            description="Learn the fundamentals of cryptocurrency and blockchain technology",
            difficulty="beginner",
            points_reward=10
        )
        db.session.add(sample_quiz)
        db.session.commit()

        # Add sample questions
        questions = [
            {
                'question_text': "What is Bitcoin?",
                'options': {
                    'a': "A digital currency",
                    'b': "A type of credit card",
                    'c': "A computer game",
                    'd': "A social media platform"
                },
                'correct_answer': "a",
                'explanation': "Bitcoin is the first and most well-known cryptocurrency, a type of digital currency."
            },
            {
                'question_text': "What is blockchain?",
                'options': {
                    'a': "A type of cryptocurrency",
                    'b': "A distributed ledger technology",
                    'c': "A computer virus",
                    'd': "A programming language"
                },
                'correct_answer': "b",
                'explanation': "Blockchain is a distributed ledger technology that records transactions across many computers."
            }
        ]

        for q in questions:
            question = Question(
                quiz_id=sample_quiz.id,
                question_text=q['question_text'],
                options=q['options'],
                correct_answer=q['correct_answer'],
                explanation=q['explanation']
            )
            db.session.add(question)

        db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)