import os

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI

from models import Entry, Experiment, File, db

# .envファイルを読み込む
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.getenv(
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    db.init_app(app)  # ここでアプリとデータベースを連携

    return app


app = create_app()


@app.route("/")
def index():
    experiments = Experiment.query.all()
    return render_template("index.html", experiments=experiments)


@app.route("/add_entry/<int:experiment_id>", methods=["GET", "POST"])
def add_entry(experiment_id):
    experiment = Experiment.query.get_or_404(experiment_id)
    if request.method == "POST":
        content = request.form["content"]
        new_entry = Entry(content=content, experiment_id=experiment_id)
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for("view_experiment", experiment_id=experiment.id))
    return render_template("add_entry.html", experiment=experiment)


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
    if request.method == "POST":
        # Entryの内容を結合して要約する
        entries_content = " ".join([entry.content for entry in experiment.entries])
        summary = summarize_experiment_content(entries_content)

    return render_template(
        "view_experiment.html", experiment=experiment, summary=summary
    )


def summarize_experiment_content(content):
    llm = OpenAI(api_key=openai_api_key)
    template = PromptTemplate(
        input_variables=["text"],
        template="""
        # Task
        Please summarize the following "experiment" using the format commonly used in the experimental section of a chemistry research paper as described in "output format".
        If no information is provided, please describe as it is.
        # Experiment
        {text}
        # Output Format
        1. Materials and Methods: List the reagents, solvents, and equipment used in the experiment, including purity and suppliers.
        2. Procedure: Describe the step-by-step procedure of the experiment, including reaction conditions, temperature, time, and pressure if applicable.
        3. Measurements: Summarize the analytical techniques used for characterization (e.g., NMR, IR, GC-MS, HPLC).
        4. Yields and Purification: Report the yields of the reactions and the purification methods used (e.g., recrystallization, extraction, distillation).
        """,
    )
    chain = LLMChain(llm=llm, prompt=template)
    summary = chain.run(content)
    return summary


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
