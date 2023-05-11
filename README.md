# CabinFever

TopHat Alternative

A website based off of tophat. Our website uses python's flask to route the different pages and sqlalchemy (SQLLite) to store all necessary data into our database.

Once a user reaches our index page ("/") the user can sign up (and specify whether the user is an instructor or student) or login to an existing account (with the preferences already predetermined). 

When the user signed in the user will be brought to the dashboard page where the user can sign up for classes or view their current classes

Project requirements:
- User accounts
    - Instructors
        - Create a new course
        - Can view the course details
    - Students
        - Enroll in courses
- User data - (Courses)
- (Websockets) Questions

Project imports:
- Flask==2.1.1
- Flask-SQLAlchemy==2.5.1
- Flask-SocketIO==6.1.1
- Werkzeug==2.0.3
