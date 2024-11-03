from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_bootstrap import Bootstrap5
from flask_login import login_required, LoginManager, current_user, login_user, logout_user
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import logging

from forms import LoginForm, RegistrationForm, NewBookForm
from models.database import db
from models.user import User
from models.book import Book
from utilities.service import check_image_url

load_dotenv()

DATABASE = os.environ.get('DATABASE')
SECRET_KEY = os.environ.get('SECRET_KEY')


def create_app(config_class=None):
    """Create and configure Flask application."""

    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    logger = logging.getLogger(__name__)
    handler = logging.FileHandler("book_lending.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if config_class:
        app.config.from_object(config_class)
        handler = logging.FileHandler("test_book_lending.log", mode="w")
        logger.setLevel(logging.DEBUG)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE
        logger.setLevel(logging.INFO)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
        logger.info(f"User went to Home Page")
        result = db.session.execute(db.select(Book).where(Book.available_for_lending == True))
        all_books = result.scalars().all()
        sorted_books = list(sorted(all_books, key=lambda book: (book.author, book.title)))
        return render_template("index.html", all_books=sorted_books, user=current_user)

    @app.route('/change_duration/<int:user_id>', methods=['POST'])
    @login_required
    def change_duration(user_id):
        user = db.get_or_404(User, user_id)
        duration = request.form.get('duration')
        if not duration or not duration.isdigit() or not (1 <= int(duration) <= 100):
            flash('Invalid duration value')
            logger.error(f'User id: {current_user.id} is trying to set invalid duration: {duration}')
            return redirect(url_for('my_books'))
        if current_user.id != user.id:
            logger.warning(f"Unauthorized user (id: {current_user.id}) is trying to change lending duration for user "
                           f"id: {user_id}")
            return abort(401)
        user.duration = int(duration)
        db.session.commit()
        logger.info(f'User id {user.id} changed lending duration to {user.duration}')
        flash("You have successfully changed lending duration")
        return redirect(url_for('my_books'))

    @app.route('/return_book/<int:book_id>')
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
            logger.warning(f"Book id: {book.id} you are trying to return not found")
            return redirect(url_for(current_page))
        validate_user = current_user.id == book.owner_id or current_user.id == book.lender_id
        if not validate_user:
            logger.info(f'Unauthorized user id:{current_user.id} is trying to return the book id: {book.id}')
            flash("There is no such book you have borrowed!", category='danger')
            return abort(401)
        book.return_date = None
        book.reserved = False
        book.lender_id = None
        book.lent_out = False
        db.session.commit()
        logger.info(f'User id: {current_user.id} returned book id: {book.id} successfully.')
        flash(f'You have returned book "{book.title}" successfully')
        return redirect(url_for(current_page))

    @app.route('/my_books')
    @login_required
    def my_books():
        """Filter your own added books and direct to my_books page."""
        logger.info(f"User id: {current_user.id} entered to My Books page")
        books = db.session.execute(db.select(Book).where(Book.owner_id == current_user.id)).scalars().all()
        due_books = [book for book in books if book.return_date is not None
                     and book.return_date < datetime.now().date()]

        if not books:
            logger.info(f"User id: {current_user.id} has no books to show in My Books page")
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
            else:
                book.available_for_lending = True
                message = f"Book {book.title} is set to available for lending."
            db.session.commit()
            logger.info(f"(Book id: {book.id}){message}")
            return jsonify(success=True, message=message)
        else:
            logger.warning(f'Unauthorized user trying to (de)activate book {book.title}!')
            return jsonify(success=False, error="You are not authorized to do that action."), 401

    @app.route('/my_reserved_books')
    @login_required
    def my_reserved_books():
        """Find books that you have reserved and direct the user to the my_reserved_books page."""
        logger.info(f"User id: {current_user.id} entered reserved books page.")
        books = db.session.execute(db.select(Book).where(Book.book_lender == current_user)
                                   .order_by(Book.id)).scalars().all()
        due_books = [book for book in books if book.return_date is not None and book.return_date < datetime.now()]
        if not books:
            logger.info(f"User id: {current_user.id} has no reserved books.")
            flash("You have no books reserved.")
        return render_template("my_reserved_books.html", my_books=books, user=current_user, due_books=due_books)

    @app.route('/reserve_book/<int:book_id>', methods=['GET', 'POST'])
    @login_required
    def reserve_book(book_id):
        """
        Reserve book if it's not reserved yet.

        :param book_id: Book.id
        :return: redirect to home page
        """
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if not book:
            logger.warning(f"User id: {current_user.id} tried to reserve book with id {book_id}. Book not found.")
            return abort(404)
        if book.owner_id == current_user.id:
            flash('You cannot reserve your own book!')
            logger.debug(f"Book owner (user id: {current_user.id}) tries to reserve his own book!")
            return redirect(url_for(current_page))
        if not book.reserved:
            book.reserved = True
            book.lender_id = current_user.id
            db.session.commit()
            logger.info(f'Book id"{book.id}" has been reserved for user id: {book.lender_id}')
            flash(f'Book "{book.title}" is reserved for You')
        else:
            logger.warning(f'Book id:{book.id} is already reserved for user id: {book.lender_id}')
            flash(f'Book "{book.title}" is already reserved')
        return redirect(url_for(current_page))

    @app.route('/receive_book/<int:book_id>', methods=['GET', 'POST'])
    @login_required
    def receive_book(book_id):
        """
        Validate book and mark book as handed over to lender.

        :param book_id: Book.id
        :return: redirect to my_reserved_books page
        """
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if book and not book.lent_out:
            if book.book_lender == current_user or book.book_owner == current_user:
                user = db.get_or_404(User, current_user.id)
                current_date = datetime.now().date()
                new_date = current_date + timedelta(days=user.duration)
                book.return_date = new_date
                book.lent_out = True
                db.session.commit()
                logger.info(f'Lender id: {current_user.id} received the book id: "{book.id}"')
                flash(f'Book "{book.title}" is handed over to lender.')
            else:
                logger.info(f"User id: {current_user.id} tried to receive book id: {book_id} that doesn't exists.")
                flash("You are not allowed to make these changes!")
                return abort(401)
            return redirect(url_for(current_page, user=current_user))
        else:
            logger.warning(f"User id: {current_user.id} tried to receive book id: {book_id}. Book already received.")
            return abort(400)

    @app.route('/cancel_reservation/<int:book_id>', methods=['GET', 'POST'])
    @login_required
    def cancel_reservation(book_id):
        """Validate that current user is book lender or book owner and cancel the reservation."""
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if not book:
            logger.warning(f"User id: {current_user.id} is trying to cancel the reservation of the"
                           f" book id: {book.id} that doesn't exist.")
            return redirect(url_for(current_page))
        if book.owner_id == current_user.id or book.book_lender == current_user:
            if not book.reserved:
                logger.warning(f"User id: {current_user.id} is trying to cancel the book id: {book.id}"
                               f" reservation while book is not reserved.")
                return abort(404)
            book.reserved = False
            book.book_lender = None
            db.session.commit()
            logger.info(f"Book id: {book.id} reservation has been cancelled successfully by user id: {current_user.id}")
            flash(f'Book "{book.title}" reservation is successfully cancelled')
        else:
            logger.warning(f"User id: {current_user.id} is trying to cancel the reservation of the book id: {book.id}")
            return abort(401)
        return redirect(url_for(current_page))

    @app.route('/available_books', methods=['GET', 'POST'])
    def available_books():
        """Return a list of available books that not reserved and direct to available books page."""
        books = (db.session.execute(db.select(Book).where(Book.reserved == False, Book.available_for_lending == True))
                 .scalars().all())
        sorted_books = list(sorted(books, key=lambda book: (book.author, book.title)))
        logger.info(f"User went to page: Available books")
        if not books:
            logger.debug("There's no available books. Returning empty list")
        return render_template("available_books.html", available_books=sorted_books, user=current_user)

    @app.route('/searchbar/', methods=['GET'])
    def searchbar():
        """
        Return a list of books that books author or title contains a search query and redirect to searchbar result page.
        """
        query = request.args.get('query')
        if query and len(query) > 0 and not query.isspace():
            query_books = db.session.execute(db.select(Book)
                                             .where(or_(Book.title.like(f"%{query}%"),
                                                        Book.author.like(f"%{query}%")))
                                             .order_by(Book.title)).scalars().all()
        else:
            query_books = []
            flash("Wrong input")
        if current_user.is_authenticated:
            logger.info(f"User id: {current_user.id} search query: {query}")
        else:
            logger.info(f"Not authenticated user search query: {query}")
        return render_template("searchbar.html", query_books=query_books, user=current_user, query=query)

    @app.route('/remove_book/<int:book_id>')
    @login_required
    def remove_book(book_id):
        """Remove a book from the database. Validate that book is not lent out and user is the owner of the book."""
        logger.info(f"User id: {current_user.id} entered remove_book with Book id: {book_id}")
        book = db.get_or_404(Book, book_id)
        current_page = request.args.get('current_page', default='home')
        if current_user.id != book.owner_id:
            logger.error(f"User id: {current_user.id} failed to remove book id: {book_id}. User is not the owner of "
                         f"the book")
            return abort(401)
        if book.lent_out or book.reserved:
            logger.error(f"User id: {current_user.id} is unable to remove book id: {book_id}. Book is lent out.")
            return abort(400)
        db.session.delete(book)
        db.session.commit()
        flash(f"Book {book.title} has been removed successfully")
        logger.info(f"User id: {current_user.id} removed successfully his own book id: {book_id}.")
        return redirect(url_for(current_page))

    @app.route('/add_book', methods=['GET', 'POST'])
    @login_required
    def add_book():
        """Create and add a new book to the lending environment. Validate and direct user to the book adding page."""
        form = NewBookForm()
        user = db.get_or_404(User, current_user.id)
        logger.info(f"User id: {current_user.id} went to add a new book page")
        if user and form.validate_on_submit():
            title = form.title.data
            author = form.author.data.title()
            image_url = form.image_url.data
            if not check_image_url(image_url):
                flash("Image URL is not valid. Please try again.")
                logger.error(f"User id: {current_user.id} failed to add book cover Image URL: {image_url} is not valid")
                return render_template('add_book.html', form=form, user=current_user)
            all_db_books = Book.query.all()
            existing_book = [book for book in all_db_books if title.lower() == book.title.lower() and author.lower() ==
                             book.author.lower()]
            if existing_book:
                logger.warning(f"User id: {current_user.id} failed to add book that already exists: {title}")
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
            db.session.add(new_book)
            db.session.commit()
            flash("Book added successfully")
            logger.info(f"User id: {current_user.id} created new book and added book into database: {new_book.title}, "
                        f"id: {new_book.id}")
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
            existing_mail = db.session.execute(db.select(User).where(User.email == email)).scalar()
            if existing_mail:
                logger.warning(f"User failed to create new user. Email: {email} address already exists.")
                flash('This email address already exists. Try to login instead.')
                return redirect(url_for('login'))
            existing_username = db.session.execute(db.select(User).where(User.username == username)).scalar()
            if existing_username:
                logger.warning(f"User failed to register with username: {username}. Username already exists.")
                flash('This username already exists.')
                return render_template('register.html', form=form, user=current_user)
            new_user = User(first_name=first_name.title(),
                            last_name=last_name.title(),
                            email=email,
                            username=username,
                            password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Your account has been created successfully.')
            logger.info(f"Created new user:\nFirst name: {new_user.first_name}\nLast name: {new_user.last_name}"
                        f"\nemail: {new_user.email}\nUsername: {new_user.username}")
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
                logger.debug(f"Failed as inserted username: {username} that not exists.")
                return redirect(url_for('login'))
            if not check_password_hash(user.password, password):
                flash('Invalid password. Please try again')
                logger.debug(f" Username: {username} failed as inserted wrong password")
                return render_template('login.html', form=form, user=current_user)
            flash(f"Logged in successfully as {user.first_name}.")
            login_user(user, remember=form.remember_me.data)
            logger.info(f"User id: {current_user.id} and username: {username} logged in.")
            return redirect(url_for('home'))
        return render_template("login.html", form=form, user=current_user)

    @app.route('/logout')
    @login_required
    def logout():
        """Logout current user and redirect to home page."""
        user_id = current_user.id
        logout_user()
        logger.info(f"User id: {user_id} logged out.")
        flash("You have been logged out. Hopefully we'll see you soon.")
        return redirect(url_for('home'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
