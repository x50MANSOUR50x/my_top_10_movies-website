from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField
from wtforms.fields.simple import PasswordField
from wtforms.validators import DataRequired
import requests
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from typing import List

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

MOVIE_DB_API_KEY = "6252df7079355ea75716016692c207e4"
MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# CREATE DB
class Base(DeclarativeBase):
    pass
                                                  #name of the db
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///my-top-10-movies-collection.db"

# Create the extension
db = SQLAlchemy(model_class=Base)
# Initialise the app with the extension
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

# CREATE TABLE
class Movie(db.Model):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, unique=False, nullable=False)
    description: Mapped[str] = mapped_column(String(300), unique=False, nullable=False)
    rating: Mapped[float] = mapped_column(Float, unique=False, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, unique=False, nullable=True)
    review: Mapped[str] = mapped_column(String(100), unique=False, nullable=True)
    img_url: Mapped[str] = mapped_column(String(200), unique=False, nullable=False)

    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="movies")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))

    movies: Mapped[List["Movie"]] = relationship(back_populates="user")

with app.app_context():
    db.create_all()

class RateMovieForm(FlaskForm):
    rating = StringField(label="Your Rating Out of 10 e.g. 7.5", validators=[DataRequired()])
    review = StringField(label="Your Review", validators=[DataRequired()])
    submit = SubmitField(label="Update")

class AddMovie(FlaskForm):
    title = StringField(label="Movie title", validators=[DataRequired()])
    submit = SubmitField(label="Search")

class RegisterForm(FlaskForm):
    name = StringField(label="Name", validators=[DataRequired()])
    email = StringField(label="Email", validators=[DataRequired()])
    password = PasswordField(label="Password", validators=[DataRequired()])
    submit = SubmitField(label="Submit")

class LoginForm(FlaskForm):
    email = StringField(label="Email", validators=[DataRequired()])
    password = PasswordField(label="Password", validators=[DataRequired()])
    submit = SubmitField(label="Submit")

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if user: #<user n> or None
            flash("This email is already in the database login instead.")
            return redirect(url_for("login"))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(
                password=password,
                method="pbkdf2:sha256",
                salt_length=8
            )
        )
        # print(new_user)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("show_movies"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if not user: #<user n> or none
            flash("This email doesn't exist in the database.")
            return redirect(url_for("login"))
        elif not check_password_hash(password=password, pwhash=user.password):
            flash("This email does exist in the database, but the password is wrong try again.")
            return redirect(url_for("login"))
        else:
            # print(user)
            # print(user.name)
            # print(user.password)

            login_user(user)

            return redirect(url_for("show_movies"))
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/show_movies")
@login_required
def show_movies():
    # result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    # all_movies = result.scalars().all() # convert ScalarResult to Python List
    all_movies = current_user.movies
    print(all_movies)
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()
    return render_template("show_movies.html", movies=all_movies)

@app.route("/add", methods=["POST", "GET"])
@login_required
def add_movie():
    form = AddMovie()
    if form.validate_on_submit():
        title = form.title.data
        # print(title)
        response = requests.get(MOVIE_DB_SEARCH_URL, params={
            "api_key": MOVIE_DB_API_KEY, "query": title})
        data = response.json()["results"]
        # print(data)
        # for movie in data:
        #     print(movie["original_title"])
        return render_template("select.html", movies=data)
    return render_template("add.html", form=form)

@app.route("/find")
@login_required
def find_movie():
    movie_api_id = request.args.get("id")
    print(movie_api_id)
    if movie_api_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_api_id}"
        #The language parameter is optional, if you were making the website for a different audience
        #e.g. Hindi speakers then you might choose "hi-IN"
        response = requests.get(movie_api_url, params={"api_key": MOVIE_DB_API_KEY, "language": "en-US"})
        data = response.json()
        new_movie = Movie(
            title=data["title"],
            #The data in release_date includes month and day, we will want to get rid of.
            year=data["release_date"].split("-")[0],
            img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            description=data["overview"],
            user_id=current_user.id
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("rate_movie", id=new_movie.id))

# Adding the Update functionality
@app.route("/edit", methods=["GET", "POST"])
@login_required
def rate_movie():
    form = RateMovieForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('show_movies'))
    return render_template("edit.html", movie=movie, form=form)

@app.route("/delete")
@login_required
def delete():
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("show_movies"))

if __name__ == '__main__':
    app.run(debug=True)
