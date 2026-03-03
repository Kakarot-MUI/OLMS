import uuid
from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager, bcrypt


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User model for authentication and profile."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user', index=True)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Student profile fields
    roll_number = db.Column(db.String(50), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    division = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.Integer, nullable=True)

    # Relationships
    issued_books = db.relationship('IssuedBook', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_active_user(self):
        return self.status == 'active'

    def __repr__(self):
        return f'<User {self.email}>'


class Book(db.Model):
    """Book model for library inventory."""
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(255), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    issued_records = db.relationship('IssuedBook', backref='book', lazy='dynamic')

    # Constraints
    __table_args__ = (
        db.CheckConstraint('total_copies >= 0', name='ck_total_copies_non_negative'),
        db.CheckConstraint('available_copies >= 0', name='ck_available_copies_non_negative'),
        db.CheckConstraint('available_copies <= total_copies', name='ck_available_lte_total'),
    )

    @property
    def is_available(self):
        return self.available_copies > 0

    def __repr__(self):
        return f'<Book {self.title}>'


class IssuedBook(db.Model):
    """Issued book tracking model."""
    __tablename__ = 'issued_books'

    id = db.Column(db.Integer, primary_key=True)
    issue_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    issue_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='issued', index=True)

    @staticmethod
    def generate_issue_code():
        """Generate a unique issue code like SL-20260303-A1B2C3."""
        date_part = datetime.utcnow().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:6].upper()
        return f'SL-{date_part}-{unique_part}'

    def __repr__(self):
        return f'<IssuedBook user={self.user_id} book={self.book_id} status={self.status}>'


class Message(db.Model):
    """Chat message between student and admin."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

    def __repr__(self):
        return f'<Message {self.sender_id}->{self.receiver_id}>'
