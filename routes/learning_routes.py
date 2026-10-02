from flask import Blueprint, render_template

learning_bp = Blueprint('learning', __name__, url_prefix='/learning')

@learning_bp.route('/learn')
def learn():
    return render_template('learning/learn.html')

@learning_bp.route('/quiz')
def quiz():
    return render_template('learning/quiz.html')

@learning_bp.route('/tutor')
def tutor():
    return render_template('learning/tutor.html')
