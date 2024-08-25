import io
import os

import markdown
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from googletrans import Translator
from langsmith import Client
from werkzeug.utils import secure_filename

import utils
from models import Entry, Experiment, File, db

# .envファイルを読み込む
load_dotenv()
allowed_extensions = os.getenv("ALLOWED_EXTENSIONS")

# LangSmithクライアントを初期化
langsmith_client = Client()


# アプリ初期化
def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.getenv(
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    )
    app.secret_key = os.getenv("SECRET_KEY")
    db.init_app(app)  # ここでアプリとデータベースを連携

    return app


app = create_app()
with app.app_context():
    db.create_all()


@app.route("/")
def index():
    experiments = Experiment.query.all()
    return render_template("index.html", experiments=experiments)


@app.route("/add_entry/<int:experiment_id>", methods=["GET", "POST"])
def add_entry(experiment_id):
    experiment = Experiment.query.get_or_404(experiment_id)
    if request.method == "POST":
        content = request.form["content"]
        # 入力されたテキストを翻訳
        translated_content = translate_text_to_english(content)
        # 新しいエントリーを保存
        new_entry = Entry(
            content=content,
            translated_content=translated_content,
            experiment_id=experiment_id,
        )
        db.session.add(new_entry)
        db.session.commit()
        # ファイルのアップロード処理
        file = request.files["file"]
        if file:
            if allowed_file(file.filename):
                file_name = secure_filename(file.filename)
                file_type = file.filename.rsplit(".", 1)[1].lower()
                file_data = file.read()  # ファイルのバイナリデータを読み込む

                # Fileモデルにファイルを保存
                new_file = File(
                    file_name=file_name,
                    file_type=file_type,
                    data=file_data,
                    entry_id=new_entry.id,
                )
                db.session.add(new_file)
                db.session.commit()
                flash("ファイル添付成功！", "success")
            else:
                flash(f"ファイル添付失敗。ファイル拡張子: {file.filename}", "danger")
            return redirect(url_for("view_experiment", experiment_id=experiment.id))
        return redirect(url_for("view_experiment", experiment_id=experiment.id))
    return render_template("add_entry.html", experiment=experiment)


# 英語への翻訳関数
def translate_text_to_english(text):
    translator = Translator()
    result = translator.translate(text).text
    return result


# ファイルアップロード前拡張子確認関数
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


@app.route("/create_experiment", methods=["GET", "POST"])
def create_experiment():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        new_experiment = Experiment(title=title, description=description)
        db.session.add(new_experiment)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("create_experiment.html")


@app.route("/experiment/<int:experiment_id>", methods=["GET", "POST"])
def view_experiment(experiment_id):
    experiment = Experiment.query.get_or_404(experiment_id)

    summary = None
    summary_html = None
    if request.method == "POST":
        # Entryの内容を結合して要約する
        entries_content = " ".join(
            [entry.translated_content for entry in experiment.entries]
        )
        summary = utils.summarize_experiment_content(entries_content)
        summary_html = markdown.markdown(summary, output_format="xhtml")

    # ローカルのJSONファイルからプロトコールデータを読み込む
    experiment_protocol = utils.load_experiment_protocol()

    return render_template(
        "view_experiment.html",
        experiment=experiment,
        summary=summary_html,
        protocol=experiment_protocol["protocol"],
    )


@app.route("/download_file/<int:file_id>")
def download_file(file_id):
    # データベースからファイルを取得
    file = File.query.get_or_404(file_id)

    # ファイルのバイナリデータを返してダウンロード可能にする
    return send_file(
        io.BytesIO(file.data),
        mimetype=f"application/{file.file_type}",
        as_attachment=True,
        download_name=file.file_name,
    )


@app.route("/delete_experiment/<int:experiment_id>", methods=["POST"])
def delete_experiment(experiment_id):
    # 実験を取得
    experiment = Experiment.query.get_or_404(experiment_id)

    # 実験に関連するすべてのエントリーとファイルを削除
    for entry in experiment.entries:
        for file in entry.attachments:
            db.session.delete(file)  # ファイルを削除
        db.session.delete(entry)  # エントリーを削除

    # 実験自体を削除
    db.session.delete(experiment)
    db.session.commit()

    flash("Experiment and all related entries and files have been deleted.", "success")
    return redirect(url_for("index"))  # 削除後にトップページにリダイレクト


if __name__ == "__main__":
    app.run(debug=True)
