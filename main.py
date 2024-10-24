from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bootstrap import Bootstrap5
from flask_login import login_required, LoginManager, current_user, login_user, logout_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, DateTime, Boolean, or_
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase, Relationship
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegistrationForm, NewBookForm
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("book_lending.log", mode="w")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
DATABASE = os.environ.get('DATABASE')
SECRET_KEY = os.environ.get('SECRET_KEY')


class Book(db.Model):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[String] = mapped_column(String(250), nullable=False, unique=True)
    author: Mapped[String] = mapped_column(String(250), nullable=False)
    image_url: Mapped[String] = mapped_column(String(250), nullable=False)
    return_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    reserved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    lent_out: Mapped[bool] = mapped_column(Boolean, nullable=False)
    available_for_lending: Mapped[bool] = mapped_column(Boolean, nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"), nullable=False)
    book_owner = Relationship('User', foreign_keys=[owner_id], back_populates='my_books')
    lender_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"), nullable=True)
    book_lender = Relationship('User', foreign_keys=[lender_id], back_populates='reserved_books')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[String] = mapped_column(String(250), nullable=False)
    last_name: Mapped[String] = mapped_column(String(250), nullable=False)
    email: Mapped[String] = mapped_column(String(250), nullable=False, unique=True)
    username: Mapped[String] = mapped_column(String(250), nullable=False, unique=True)
    password: Mapped[String] = mapped_column(String(250), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    my_books = Relationship('Book', foreign_keys='Book.owner_id', back_populates='book_owner')
    reserved_books = Relationship('Book', foreign_keys='Book.lender_id', back_populates='book_lender')


def create_app(config_class=None):
    """Create and configure Flask application."""
    app = Flask(__name__)

    if config_class:
        app.config.from_object(config_class)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    app.config['SECRET_KEY'] = SECRET_KEY
    Bootstrap5(app)

    login_manager = LoginManager(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return db.get_or_404(User, user_id)

    @app.route('/')
    def home():
        """
        Main Page.

        Show all the books in the database.
        """
        logger.info("Went to Home Page")
        result = db.session.execute(db.select(Book).where(Book.available_for_lending == True).order_by(Book.title))
        all_books = result.scalars().all()
        return render_template("index.html", all_books=all_books, user=current_user)

    @app.route('/change_duration/<int:user_id>', methods=['POST'])
    @login_required
    def change_duration(user_id):
        user = db.get_or_404(User, user_id)
        duration = request.form.get('duration')
        if user and duration and request.method == 'POST':
            user.duration = int(duration)
            db.session.commit()
            logger.info(f'User changed lending duration to {user.duration}')
            flash("You have successfully changed lending duration")
        else:
            logger.warning("Unknown user trying to change lending duration")
            flash("Oops, something went wrong")
        return redirect(url_for('my_books'))

    @app.route('/return_book/<book_id>')
    @login_required
    def return_book(book_id):
        """
        Return book to lending environment.

        Validate book and user. Book can return only book lender or book owner.
        Reset book values.
        :param book_id: Book id
        :return: redirect to home page.
        """
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if not book:
            flash('Book not found')
            logger.warning("Book you are trying to return not found")
            return redirect(url_for(current_page))
        validate_user = current_user.id == book.lender_id or current_user.id == book.owner_id
        if not validate_user:
            logger.info(f'Unauthorized user is trying to return the book "{book.title}"')
            flash("There is no such book you have borrowed!", category='danger')
            return redirect(url_for(current_page))
        book.return_date = None
        book.reserved = False
        book.lender_id = None
        book.lent_out = False
        db.session.commit()
        logger.info(f'User returned book "{book.title}" successfully.')
        flash(f'You have returned book "{book.title}" successfully')
        return redirect(url_for(current_page))

    @app.route('/my_books')
    def my_books():
        """Filter your own added books and direct to my_books page."""
        logger.info("Went to My Books page")
        books = db.session.execute(db.select(Book).where(Book.owner_id == current_user.id)).scalars().all()
        due_books = [book for book in books if book.return_date is not None and book.return_date < datetime.now()]

        if not books:
            logger.info("User has no books to show in My Books page")
            flash("You haven't added any books yet")
        return render_template("my_books.html", user=current_user, books=books, due_books=due_books)

    @app.route('/activate_to_borrow/<int:book_id>')
    @login_required
    def activate_to_borrow(book_id):
        """Activate or deactivate your own book for lending out."""
        book = db.get_or_404(Book, book_id)
        if book and book.owner_id == current_user.id and book.lent_out is False:
            if book.available_for_lending:
                book.available_for_lending = False
                message = f"Book {book.title} is set to unavailable for lending."
                logger.info(message)
            else:
                book.available_for_lending = True
                message = f"Book {book.title} is set to available for lending."
                logger.info(message)
            db.session.commit()
            return jsonify(success=True, message=message)
        else:
            logger.warning(f'Unauthorized user trying to (de)activate book {book.title}!')
            return jsonify(success=False, error="You are not authorized to do that action.")

    @app.route('/my_reserved_books')
    def my_reserved_books():
        """Find books that you have reserved and direct the user to the my_reserved_books page."""
        books = db.session.execute(db.select(Book).where(Book.book_lender == current_user)
                                   .order_by(Book.id)).scalars().all()
        due_books = [book for book in books if book.return_date is not None and book.return_date < datetime.now()]
        if not books:
            logger.info("User has no reserved books.")
            flash("You have no books reserved.")
        return render_template("my_reserved_books.html", my_books=books, user=current_user, due_books=due_books)

    @app.route('/reserve_book/<book_id>', methods=['GET', 'POST'])
    @login_required
    def reserve_book(book_id):
        """
        Reserve book if it's not reserved yet.

        :param book_id: Book.id
        :return: redirect to home page
        """
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if book.owner_id == current_user.id:
            flash('You cannot reserve your own book!')
            logger.debug("Book owner tries to reserve his own book!")
            return redirect(url_for(current_page))
        if book and not book.reserved:
            book.reserved = True
            book.lender_id = current_user.id
            db.session.commit()
            logger.info(f'Book "{book.title}" has been reserved for user id: {book.lender_id}')
            flash(f'Book "{book.title}" is reserved for You')
        else:
            logger.warning(f'Book "{book.title}" is already reserved for user id: {book.lender_id}')
            flash(f'Book "{book.title}" is already reserved')
        return redirect(url_for(current_page))

    @app.route('/hand_over/<book_id>', methods=['GET', 'POST'])
    @login_required
    def receive_book(book_id):
        """
        Validate book and mark book as handed over to lender.

        :param book_id: Book.id
        :return: redirect to my_reserved_books page
        """
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if book:
            if book.book_lender == current_user or book.book_owner == current_user:
                current_date = datetime.now()
                new_date = current_date + timedelta(days=28)
                book.return_date = new_date
                book.lent_out = True
                db.session.commit()
                logger.info(f'Lender received the book: "{book.title}"')
                flash(f'Book "{book.title}" is handed over to lender')
            else:
                logger.info(f"Book doesn't exists.")
                flash("You are not allowed to make these changes!")
            return redirect(url_for(current_page, user=current_user))

    @app.route('/cancel_reservation/<book_id>', methods=['GET', 'POST'])
    @login_required
    def cancel_reservation(book_id):
        """Validate that current user is book lender or book owner and cancel the reservation."""
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if not book:
            logger.warning("You are trying to cancel the reservation of the book that doesn't exist.")
            flash("There's no such book")
            return redirect(url_for(current_page))
        if book.book_lender == current_user or book.owner_id == current_user.id:
            book.reserved = False
            book.book_lender = None
            db.session.commit()
            logger.info(f"Book {book.title} reservation has been cancelled")
            flash(f'Book "{book.title}" reservation is successfully cancelled')
        else:
            logger.warning("You are trying to cancel the reservation of the")
            flash("You are not authorized to cancel the reservation")
        return redirect(url_for(current_page))

    @app.route('/available_books', methods=['GET', 'POST'])
    def available_books():
        """Return a list of available books that not reserved and direct to available books page."""
        books = (db.session.execute(db.select(Book).where(Book.reserved == False, Book.available_for_lending == True))
                 .scalars().all())
        if not books:
            logger.debug("There's no available books. Returning empty list")
        return render_template("available_books.html", available_books=books, user=current_user)

    @app.route('/searchbar/', methods=['GET'])
    def searchbar():
        """Return a list of books that books author or title contains a search term and direct to searchbar result page."""
        query = request.args.get('query')
        if query:
            query_books = db.session.execute(db.select(Book)
                                             .where(or_(Book.title.like(f"%{query}%"),
                                                        Book.author.like(f"%{query}%")))
                                             .order_by(Book.title)).scalars().all()
        else:
            query_books = []
        logger.info(f"Search query: {query}")
        return render_template("searchbar.html", query_books=query_books, user=current_user, query=query)

    @app.route('/add_book', methods=['GET', 'POST'])
    @login_required
    def add_book():
        """Create and add a new book to the lending environment. Validate and direct user to the book adding page."""
        form = NewBookForm()
        user = db.get_or_404(User, current_user.id)
        if user and form.validate_on_submit():
            title = form.title.data.title()
            author = form.author.data.title()
            image_url = form.image_url.data
            existing_book = db.session.execute(
                db.select(Book).where(Book.title == title, Book.author == author)
            ).scalar_one_or_none()
            if existing_book:
                logger.warning(f"Book already exists: {title}")
                flash("A book with this title already exists.", "danger")

                return redirect(url_for('add_book'))
            new_book = Book(title=title,
                            author=author,
                            image_url=image_url,
                            return_date=None,
                            reserved=False,
                            lent_out=False,
                            owner_id=user.id,
                            available_for_lending=True)
            logging.info(f'Created new book: {title}.')
            db.session.add(new_book)
            db.session.commit()
            flash("Book added successfully")
            logger.info(f"Added new book into database: {new_book.title}")
            return redirect(url_for('home'))
        return render_template("add_book.html", form=form, user=current_user)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """
        Register new user to environment.

        Validate user data and redirect to Home Page.
        """
        form = RegistrationForm()
        if form.validate_on_submit():
            first_name = form.first_name.data
            last_name = form.last_name.data
            email = form.email.data
            username = form.username.data
            password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )
            existing_user = db.session.execute(db.select(User).where(User.email == email)).scalar()
            if existing_user:
                logger.warning("User already exists.")
                flash('This email address already exists. Try to login instead.')
                return redirect(url_for('login'))
            new_user = User(first_name=first_name.title(),
                            last_name=last_name.title(),
                            email=email,
                            username=username,
                            password=password,
                            duration=28)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Your account has been created successfully.')
            logger.info(f"Created new user: {new_user.first_name} {new_user.last_name}")
            return redirect(url_for('home'))
        return render_template("register.html", form=form, user=current_user)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Validate user username and password to log user in."""
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            user = db.session.execute(db.select(User).where(User.username == username)).scalar()
            if not user:
                flash('Invalid Username. Please try again')
                logger.debug("Inserted invalid Username")
                return redirect(url_for('login'))
            if not check_password_hash(user.password, password):
                flash('Invalid password. Please try again')
                logger.debug("Inserted wrong password")
                return render_template('login.html', form=form, user=current_user)
            flash(f"Logged in successfully as {user.first_name}.")
            login_user(user, remember=form.remember_me.data)
            logger.info("User logged in.")
            return redirect(url_for('home'))
        return render_template("login.html", form=form, user=current_user)

    @app.route('/logout')
    @login_required
    def logout():
        """Logout current user and redirect to home page."""
        if not current_user.is_authenticated:
            flash('You must be logged in to log out')
            return redirect(url_for('login'))
        logout_user()
        logger.info("User logged out.")
        flash("You have been logged out. Hopefully we'll see you soon.")
        return redirect(url_for('home'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
