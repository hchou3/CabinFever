from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = '315-at-165'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tophat.db'
db = SQLAlchemy(app)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor = db.relationship('User', backref=db.backref('courses_taught', lazy=True))

enrollments = db.Table('enrollments',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(15), nullable=False)
    courses_enrolled = db.relationship('Course', secondary=enrollments, backref=db.backref('students', lazy=True))

def create_tables():
    with app.app_context():
        db.create_all()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password, method='sha256')

        user = User(username=username, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')


def is_instructor(user_id):
    user = User.query.get(user_id)
    return user.role == 'instructor'

@app.route('/dashboard')
def dashboard():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    courses = user.courses_enrolled
    all_courses = Course.query.all()
    return render_template('dashboard.html', user=user, courses=courses, all_courses=all_courses)

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if not is_instructor(session['user_id']):
        abort(403)

    return render_template('create_course.html')

    # Implement course creation 

@app.route('/create_question/<int:course_id>', methods=['GET', 'POST'])
def create_question(course_id):
    if not is_instructor(session['user_id']):
        abort(403)

    # Implement question creation 

@app.route('/start_question/<int:course_id>/<int:question_id>')
def start_question(course_id, question_id):
    if not is_instructor(session['user_id']):
        abort(403)

    # Implement starting question 

@app.route('/stop_question/<int:course_id>/<int:question_id>')
def stop_question(course_id, question_id):
    if not is_instructor(session['user_id']):
        abort(403)


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
