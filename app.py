from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = '315-at-165'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tophat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor = db.relationship('User', backref=db.backref('courses_taught', lazy=True))

    students = db.relationship('User', secondary='enrollments', back_populates='courses_enrolled')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    courses_enrolled = db.relationship('Course', secondary='enrollments', back_populates='students')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    course = db.relationship('Course', backref=db.backref('questions', lazy=True))

enrollments = db.Table('enrollments',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')

        user = User(username=username, password=hashed_password)
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

@app.route('/dashboard')
def dashboard():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    courses = user.courses_enrolled

    all_courses = Course.query.all()
    return render_template('dashboard.html', user=user, courses=courses, all_courses=all_courses)

@app.route('/my_courses')
def my_courses():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    courses = user.courses_enrolled

    return render_template('my_courses.html', courses=courses, user=user)

@app.route('/available_courses')
def available_courses():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    all_courses = Course.query.all()
    enrolled_courses = user.courses_enrolled

    return render_template('available_courses.html', all_courses=all_courses, enrolled_courses=enrolled_courses)

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if request.method == 'POST':
        course_name = request.form.get('name')

        if not course_name:
            flash('Course name is required.')
            return redirect(url_for('create_course'))

        instructor_id = session['user_id']

        course = Course(name=course_name, instructor_id=instructor_id)
        db.session.add(course)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template('create_course.html')

@app.route('/gradebook/<int:course_id>')
def gradebook(course_id):
    course = Course.query.get_or_404(course_id)

    return render_template('gradebook.html', course=course)

@app.route('/my_grades')
def my_grades():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    return render_template('my_grades.html')

@app.route('/course_detail/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session['user_id'])
    question = Question.query.filter_by(course_id=course_id, is_active=True).first()
    return render_template('course_detail.html', course=course, user=user, course_id=course_id, question=question)

@app.route('/enroll/<int:course_id>', methods=['POST'])
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session['user_id'])

    if user in course.students:
        flash('You are already enrolled in this course.')
    else:
        course.students.append(user)
        db.session.commit()
        flash('You have successfully enrolled in the course.')

    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/create_question/<int:course_id>', methods=['GET', 'POST'])
def create_question(course_id):
    if request.method == 'POST':
        question_text = request.form.get('text')
        answers = {
            'A': request.form.get('answerA'),
            'B': request.form.get('answerB'),
            'C': request.form.get('answerC'),
            'D': request.form.get('answerD')
        }
        correct_answer = request.form.get('correct_answer')

        if not question_text or not all(answers.values()):
            flash('All fields are required.')
            return redirect(url_for('create_question', course_id=course_id))

        question = Question(course_id=course_id, text=question_text, correct_answer=correct_answer, is_active=False)
        db.session.add(question)
        db.session.commit()

        question_data = {
            'text': question_text,
            'course_id': course_id,
            'question_id': question.id,
            'answers': answers
        }
        socketio.emit('new_question', question_data, room=str(course_id))
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('create_question.html', course_id=course_id)


def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    socketio.run(app, host='0.0.0.0', port=8000)
