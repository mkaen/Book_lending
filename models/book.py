from datetime import date

from sqlalchemy import Integer, String, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, Relationship

from models.database import db


class Book(db.Model):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[String] = mapped_column(String(250), nullable=False, unique=True)
    author: Mapped[String] = mapped_column(String(250), nullable=False)
    image_url: Mapped[String] = mapped_column(String(250), nullable=False)
    return_date: Mapped[date] = mapped_column(Date, nullable=True, default=None)
    reserved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lent_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    available_for_lending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    owner_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"), nullable=False)
    book_owner = Relationship('User', foreign_keys=[owner_id], back_populates='my_books')
    lender_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"), nullable=True)
    book_lender = Relationship('User', foreign_keys=[lender_id], back_populates='reserved_books')
