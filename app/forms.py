from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, IntegerField,
    SelectField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, ValidationError, Optional
)
from app.models import User


class RegistrationForm(FlaskForm):
    """User registration form with validation."""
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=120, message='Name must be between 2 and 120 characters.')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ])
    roll_number = StringField('Roll Number', validators=[
        DataRequired(message='Roll number is required.'),
        Length(min=1, max=50)
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required.'),
        Length(min=10, max=20, message='Enter a valid phone number.')
    ])
    division = StringField('Division', validators=[
        DataRequired(message='Division is required.'),
        Length(min=1, max=20)
    ])
    department = SelectField('Department', validators=[
        DataRequired(message='Department is required.')
    ], choices=[
        ('', '-- Select Department --'),
        ('Computer Science', 'Computer Science'),
        ('Information Technology', 'Information Technology'),
        ('Electronics', 'Electronics'),
        ('Mechanical', 'Mechanical'),
        ('Civil', 'Civil'),
        ('Electrical', 'Electrical'),
        ('Chemical', 'Chemical'),
        ('Other', 'Other'),
    ])
    semester = SelectField('Semester', coerce=int, validators=[
        DataRequired(message='Semester is required.')
    ], choices=[
        (0, '-- Select Semester --'),
        (1, 'Semester 1'), (2, 'Semester 2'),
        (3, 'Semester 3'), (4, 'Semester 4'),
        (5, 'Semester 5'), (6, 'Semester 6'),
        (7, 'Semester 7'), (8, 'Semester 8'),
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=6, max=128, message='Password must be at least 6 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('This email is already registered.')


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    submit = SubmitField('Login')


class BookForm(FlaskForm):
    """Book add/edit form."""
    title = StringField('Title', validators=[
        DataRequired(message='Title is required.'),
        Length(min=1, max=255)
    ])
    author = StringField('Author', validators=[
        DataRequired(message='Author is required.'),
        Length(min=1, max=255)
    ])
    category = StringField('Category', validators=[
        DataRequired(message='Category is required.'),
        Length(min=1, max=100)
    ])
    total_copies = IntegerField('Total Copies', validators=[
        DataRequired(message='Total copies is required.'),
        NumberRange(min=1, message='Must have at least 1 copy.')
    ])
    submit = SubmitField('Save Book')


class IssueBookForm(FlaskForm):
    """Form to issue a book to a user."""
    user_id = SelectField('Select Member', coerce=int, validators=[
        DataRequired(message='Please select a member.')
    ])
    book_id = SelectField('Select Book', coerce=int, validators=[
        DataRequired(message='Please select a book.')
    ])
    issue_days = IntegerField('Borrow Duration (Days)', default=14, validators=[
        DataRequired(message='Duration is required.'),
        NumberRange(min=1, max=365, message='Duration must be between 1 and 365 days.')
    ])
    submit = SubmitField('Issue Book')


class ReturnBookForm(FlaskForm):
    """Form to return a book."""
    issue_id = HiddenField('Issue ID', validators=[
        DataRequired()
    ])
    submit = SubmitField('Return Book')


class EditDueDateForm(FlaskForm):
    """Form to edit due date of an issued book."""
    due_date = StringField('New Due Date', validators=[
        DataRequired(message='Due date is required.')
    ])
    submit = SubmitField('Update Due Date')


class SearchForm(FlaskForm):
    """Book search form."""
    query = StringField('Search', validators=[
        Length(max=255)
    ])
    category = SelectField('Category', choices=[('', 'All Categories')], validate_choice=False)
    submit = SubmitField('Search')


class StudentProfileForm(FlaskForm):
    """Student profile edit form."""
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=120)
    ])
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(min=10, max=20, message='Enter a valid phone number.')
    ])
    division = StringField('Division', validators=[
        Optional(), Length(max=20)
    ])
    department = SelectField('Department', validators=[Optional()], choices=[
        ('', '-- Select Department --'),
        ('Computer Science', 'Computer Science'),
        ('Information Technology', 'Information Technology'),
        ('Electronics', 'Electronics'),
        ('Mechanical', 'Mechanical'),
        ('Civil', 'Civil'),
        ('Electrical', 'Electrical'),
        ('Chemical', 'Chemical'),
        ('Other', 'Other'),
    ])
    semester = SelectField('Semester', coerce=int, validators=[Optional()], choices=[
        (0, '-- Select Semester --'),
        (1, 'Semester 1'), (2, 'Semester 2'),
        (3, 'Semester 3'), (4, 'Semester 4'),
        (5, 'Semester 5'), (6, 'Semester 6'),
        (7, 'Semester 7'), (8, 'Semester 8'),
    ])
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[
        Optional(),
        Length(min=6, max=128, message='Password must be at least 6 characters.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Save Changes')


class AdminProfileForm(FlaskForm):
    """Admin profile edit form."""
    name = StringField('Full Name', validators=[
        DataRequired(message='Name is required.'),
        Length(min=2, max=120)
    ])
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[
        Optional(),
        Length(min=6, max=128, message='Password must be at least 6 characters.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Save Changes')
