import json
import os

from dotenv import load_dotenv
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

# .envファイルを読み込む
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


# TypedDict
class Summary(BaseModel):
    MaterialsAndMethods: str = Field(
        description="List the reagents, solvents, and equipment used in the experiment, including purity and suppliers."
    )
    Procedure: str = Field(
        description="step-by-step procedure of the experiment, including reaction conditions, temperature, time, and pressure if applicable."
    )
    Measurements: str = Field(
        description="the analytical techniques used for characterization (e.g., NMR, IR, GC-MS, HPLC)."
    )
    YieldsAndResults: str = Field(
        description="yields of the reactions and/or the outcome of the experiment."
    )


def summarize_experiment_content(content):
    llm = ChatOpenAI(
        api_key=openai_api_key, model="gpt-4o-2024-05-13", temperature=0.3
    )  # ChatOpenAIに変更し、モデル指定

    # ChatPromptTemplateを使用したプロンプト定義
    system_message = SystemMessagePromptTemplate.from_template(
        "You are a helpful assistant that summarizes chemistry experiments."
    )
    user_message = HumanMessagePromptTemplate.from_template(
        """
        # Task
        Please summarize the following "experiment" using the format commonly used in the experimental section of a chemistry research paper.
        Use output format as an output example.
        If no information is provided, please describe as it is.
        # Experiment
        {text}
        # Output Format
        MaterialsAndMethods:
        List the reagents, solvents, and equipment used in the experiment, including purity and suppliers.

        Procedure:
        Describe the step-by-step procedure of the experiment, including reaction conditions, temperature, time, and pressure if applicable.

        Measurements:
        Summarize the analytical techniques used for characterization (e.g., NMR, IR, GC-MS, HPLC).

        YieldsAndResults:
        Report the yields of the reactions and/or the outcome of the experiment.
        """
    )
    chat_prompt = ChatPromptTemplate.from_messages([system_message, user_message])
    output_parser = StrOutputParser()

    chain = chat_prompt | llm | output_parser
    summary_temp = chain.invoke({"text": content})
    summary = summarize_experiment_procedure(summary_temp)
    return summary


def summarize_experiment_procedure(content):
    llm = ChatOpenAI(
        api_key=openai_api_key, model="gpt-4o-2024-05-13", temperature=0.2
    )  # ChatOpenAIに変更し、モデル指定
    structured_llm = llm.with_structured_output(Summary)
    system_message = SystemMessagePromptTemplate.from_template(
        "You are a helpful assistant that summarizes chemistry experiments."
    )
    example = load_experiment_protocol()
    user_message = HumanMessagePromptTemplate.from_template(
        """
        Desribe experiment procedure in a step-by-step list, and make out put in a json format seen in a format example.
        Number of steps can be added freely so that details can be recorded to meke this experiment reproducible.
        # Procedure
        {text}
        # Format example
        {example}
        """
    )
    chat_prompt = ChatPromptTemplate.from_messages([system_message, user_message])
    output_parser = StrOutputParser()

    chain = chat_prompt | llm | output_parser
    procedures = chain.invoke({"text": content, "example": example})
    return procedures


def load_experiment_protocol():
    with open("static/json/experiment_protocol2.json", "r") as f:
        protocol = json.load(f)
    return protocol
