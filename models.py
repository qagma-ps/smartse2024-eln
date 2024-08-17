from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Experiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    entries = db.relationship("Entry", backref="experiment", lazy=True)


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    experiment_id = db.Column(
        db.Integer, db.ForeignKey("experiment.id"), nullable=False
    )
    attachments = db.relationship("File", backref="entry", lazy=True)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(100), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey("entry.id"), nullable=False)
