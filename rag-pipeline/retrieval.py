from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models import ChatOllama
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

persist_directory = "chroma_db"
embeddings = HuggingFaceEmbeddings(
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
)
guidance_vs = Chroma(
    persist_directory="chroma_db/guidelines",
    embedding_function=embeddings
).as_retriever(search_kwargs={"k": 500})  

templates_vs = Chroma(
    persist_directory="chroma_db/templates",
    embedding_function=embeddings
).as_retriever(search_kwargs={"k": 3})

sars_vs = Chroma(
    persist_directory="chroma_db/sars",
    embedding_function=embeddings
).as_retriever(search_kwargs={"k": 3})

# prompt template 
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                You are a UK SAR narrative generation engine.

                You MUST strictly follow the SAR template provided in the context.
                Do NOT modify section headings.
                Do NOT remove sections.
                Do NOT add new sections.
                Populate each section using the case data provided.

                STRICT RULES:
                - Formal third-person tone.
                - Chronological order.
                - No internal system names.
                - No model scores, confidence levels, or reasoning IDs.
                - No internal transaction IDs unless regulator-required.
                - If data is missing, write: "Information not available at time of submission."

                Return the completed template only.
                """
                        ),
                        (
                            "human",
                            """
                TEMPLATE:
                {template}

                GUIDANCE:
                {guidance}

                CASE DATA:
                {case_data}
            """
        )
    ]
)

# streamlit framework
st.title('RAG Demo')
input_text = st.text_input("Search the topic you want")

# Ollama llm
llm = ChatOllama(
    model="gemma3",
    temperature=0.5
)
output_parser = StrOutputParser()
chain = prompt | llm | output_parser

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

if input_text:

    # Retrieve relevant guidance
    guidance_docs = guidance_vs.invoke("")

    # Retrieve template
    template_docs = templates_vs.invoke(input_text)

    # Retrieve similar historical SARs (optional support context)
    sars_docs = sars_vs.invoke(input_text)

    guidance = format_docs(guidance_docs)
    template = format_docs(template_docs)
    similar_cases = format_docs(sars_docs)

    response = chain.invoke({
        "template": template,
        "guidance": guidance,
        "case_data": input_text + "\n\nSimilar Cases:\n" + similar_cases
    })

    st.subheader("Generated UK SAR Narrative")
    st.write(response)
