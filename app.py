from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, emit
from datetime import timedelta

import html
import json
config = json.load(open('config.json'))

app = Flask(__name__)
app.config['SECRET_KEY'] = config['secret']
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

class QuestionAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    course = db.relationship('Course')
    grade = db.Column(db.Integer(), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('question_answers', lazy=True))
    question = db.relationship('Question', backref=db.backref('question_answers', lazy=True))
    answer = db.relationship('Answer', backref=db.backref('question_answers', lazy=True))

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    choice_abc = db.Column(db.String(1), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    # question = db.relationship('Question', backref=db.backref('answers', lazy=True))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    answers = db.relationship('Answer', backref=db.backref('question', lazy=False))
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
        username = html.escape(request.form['username'])
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
        username = html.escape(request.form['username'])
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=24)

            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))
    
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

    courses = Course.query.filter_by(instructor_id=user.id).all()

    return render_template('my_courses.html', courses=courses, user=user)

@app.route('/available_courses')
def available_courses():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    all_courses = Course.query.filter(Course.instructor_id != user.id).all()
    enrolled_courses = user.courses_enrolled

    return render_template('available_courses.html', all_courses=all_courses, enrolled_courses=enrolled_courses)

@app.route('/enrolled_courses')
def enrolled_courses():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    enrolled_courses = user.courses_enrolled

    return render_template('enrolled_courses.html', enrolled_courses=enrolled_courses, user=user)


@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if request.method == 'POST':
        course_name = html.escape(request.form.get('name'))

        if not course_name:
            flash('Course name is required.')
            return redirect(url_for('create_course'))

        instructor_id = session['user_id']
        instructor = User.query.get(instructor_id)

        course = Course(name=course_name, instructor_id=instructor_id)
        # instructor.courses_enrolled.append(course)

        db.session.add(course)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template('create_course.html')


@app.route('/gradebook/<int:course_id>')
def gradebook(course_id):
    course = Course.query.get_or_404(course_id)

    graded_questions = QuestionAnswer.query.filter_by(course_id=course_id).all()

    return render_template('gradebook.html', course=course, graded_questions=graded_questions)

@app.route('/my_grades')
def my_grades():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)
    print(user)
    graded_questions = QuestionAnswer.query.filter_by(user_id=user.id).all()
    print("graded questions", graded_questions)
    course_map = {}
    for question in graded_questions:
        correct_ans = Answer.query.filter_by(
            question_id=question.question.id, choice_abc=question.question.correct_answer
        ).first()
        question.correct_ans = correct_ans
        course_id = question.course_id
        course = Course.query.get(course_id)
        if course not in course_map:
            course_map[course] = [question]
        else:
            course_map[course].append(question)

    print("course map", course_map)
    return render_template('my_grades.html', graded_questions=course_map, user=user)

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

    if user.id == course.instructor_id:
        flash('You are the instructor for this course and cannot enroll.')
    elif user in course.students:
        flash('You are already enrolled in this course.')
    else:
        course.students.append(user)
        db.session.commit()
        flash('You have successfully enrolled in the course.')

    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/create_question/<int:course_id>', methods=['GET', 'POST'])
def create_question(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session['user_id'])

    if user.id != course.instructor_id:
        flash('Only the instructor of the course can create questions.')
        return redirect(url_for('course_detail', course_id=course_id))

    if request.method == 'POST':
        question_text = html.escape(request.form.get('text'))
        answers = {
            'A': html.escape(request.form.get('answerA')),
            'B': html.escape(request.form.get('answerB')),
            'C': html.escape(request.form.get('answerC')),
            'D': html.escape(request.form.get('answerD'))
        }
        correct_answer = request.form.get('correct_answer')

        if not question_text or not all(answers.values()):
            flash('All fields are required.')
            return redirect(url_for('create_question', course_id=course_id))

        question = Question(course_id=course_id, text=question_text, correct_answer=correct_answer, is_active=True)
        db.session.add(question)
        db.session.commit()

        for answerKey in answers:
            answer = Answer(text=answers[answerKey], question_id=question.id, choice_abc=answerKey)
            db.session.add(answer)
        db.session.commit()

        answer_id_dict = {x.id: x.text for x in question.answers}
        question_data = {
            'text': question_text,
            'course_id': course_id,
            'question_id': question.id,
            'answers': answer_id_dict
        }
        print(question_data)
        socketio.emit('new_question', question_data, room='course_'+str(course_id))
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('create_question.html', course_id=course_id)

# start question

# stop question

# view grades 
    # instructor of class can see all grades
    # user can only see their grade

# security

@socketio.on('join')
def on_join(data):
    rooms = data['rooms']
    for room in rooms:
        print("Joining room: " + str(room))
        join_room(room)

@socketio.on('stop_question')
def on_stop_question(data):
    print("stop question", data)
    course_id = data['course_id']
    # get all active questions for course and mark non active
    questions = Question.query.filter_by(course_id=course_id, is_active=True).all()
    for question in questions:
        question.is_active = False
        db.session.commit()
    emit('question_stopped', {'course_id': course_id}, room='course_'+str(course_id))

@socketio.on('submit_answer')
def on_submit_answer(data):
    print("submit answer", data)
    user_id = data['user_id']
    question_id = data['question_id']
    answer_id = data['answer_id']

    question = Question.query.get(question_id)
    if not question or not question.is_active:
        emit('answer_result', {'result': 'fail', 'message': 'Question is not active'}, room='user_'+user_id)
        return

    answer = Answer.query.filter_by(question_id=question_id, id=int(answer_id)).first()
    if not answer:
        emit('answer_result', {'result': 'fail', 'message': 'Invalid answer'}, room='user_'+user_id)
        return

    question_answer = QuestionAnswer(
        user_id=user_id, question_id=question_id,
        answer_id=answer.id,
        course_id=question.course_id
    )
    
    if answer.choice_abc == question.correct_answer:
        question_answer.grade = 100
    else:
        question_answer.grade = 0

    db.session.add(question_answer)
    db.session.commit()
    print('emitting answer result')
    emit('answer_result', {'result': 'success', 'grade': question_answer.grade}, room='user_'+user_id)

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=1)
    session.modified = True


def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    socketio.run(app, host='0.0.0.0', port=80, debug=True)
