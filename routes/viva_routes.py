from flask import Blueprint, render_template

viva_bp = Blueprint('viva', __name__, url_prefix='/viva')

@viva_bp.route('/')
def viva_index():
    return render_template('viva/viva.html')

@viva_bp.route('/result')
def result():
    return render_template('viva/viva_result.html')
