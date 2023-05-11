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

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    course = db.relationship('Course', backref=db.backref('questions', lazy=True))

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    question = db.relationship('Question', backref=db.backref('answers', lazy=True))

class QuestionAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('question_answers', lazy=True))
    question = db.relationship('Question', backref=db.backref('question_answers', lazy=True))
    answer = db.relationship('Answer', backref=db.backref('question_answers', lazy=True))

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

@app.route('/dashboard')
def dashboard():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    if user.role == 'instructor':
        courses = user.courses_taught
    elif user.role == 'student':
        courses = user.courses_enrolled
    else:
        courses = []

    all_courses = Course.query.all()
    return render_template('dashboard.html', user=user, courses=courses, all_courses=all_courses)

def is_instructor(user_id):
    user = User.query.get(user_id)
    return user.role == 'instructor'

@app.route('/my_courses')
def my_courses():
    user = User.query.get(session['user_id'])
    if not user:
        abort(403)

    if user.role == 'instructor':
        courses = user.courses_taught
    elif user.role == 'student':
        courses = user.courses_enrolled
    else:
        courses = []

    return render_template('my_courses.html', courses=courses, user=user)

@app.route('/available_courses')
def available_courses():
    user = User.query.get(session['user_id'])
    print(user)
    if not user:
        abort(403)

    all_courses = Course.query.all()
    enrolled_courses = user.courses_enrolled

    return render_template('available_courses.html', all_courses=all_courses, enrolled_courses=enrolled_courses)

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if not is_instructor(session['user_id']):
        abort(403)

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

@app.route('/course_detail/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session['user_id'])
    return render_template('course_detail.html', course=course, user=user)

@app.route('/enroll/<int:course_id>', methods=['POST'])
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session['user_id'])

    if user.role == 'instructor':
        flash('Instructors cannot enroll in a course.')
        return redirect(url_for('course_detail', course_id=course_id))

    if user in course.students:
        flash('You are already enrolled in this course.')
    else:
        course.students.append(user)
        db.session.commit()
        flash('You have successfully enrolled in the course.')

    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/create_question/<int:course_id>', methods=['GET', 'POST'])
def create_question(course_id):
    if not is_instructor(session['user_id']):
        abort(403)

    if request.method == 'POST':
        question_text = request.form.get('text')
        
        if not question_text:
            flash('Question text is required.')
            return redirect(url_for('create_question', course_id=course_id))

        question = Question(course_id=course_id, text=question_text)
        db.session.add(question)
        db.session.commit()

        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('create_question.html')

@app.route('/start_question/<int:course_id>/<int:question_id>')
def start_question(course_id, question_id):
    if not is_instructor(session['user_id']):
        abort(403)

    # Implement starting question 

@app.route('/stop_question/<int:course_id>/<int:question_id>')
def stop_question(course_id, question_id):
    if not is_instructor(session['user_id']):
        abort(403)

    # Implement stopping question 

@app.route('/submit_answer/<int:question_id>', methods=['POST'])
def submit_answer(question_id):
    user = User.query.get(session['user_id'])
    if not user or user.role != 'student':
        abort(403)

    # Implement submit answer

@app.route('/view_answers/<int:question_id>')
def view_answers(question_id):
    if not is_instructor(session['user_id']):
        abort(403)

    # Implement view answers

def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
