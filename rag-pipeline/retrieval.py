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
            "You are a helpful assistant. Answer clearly and concisely."
        ),
        (
            "human",
            "Context: \n {context} \n\n Question: {question}"
        )
    ]
)
# streamlit framework
st.title('RAG Demo')
input_text = st.text_input("Search the topic you want")

# Ollama llm
llm = ChatOllama(
    model="gemma3",
    temperature=1
)
output_parser = StrOutputParser()
chain = prompt | llm | output_parser

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

if input_text:
    guidance_docs = guidance_vs.invoke("") 
    templates_docs = templates_vs.invoke(input_text)
    sars_docs = sars_vs.invoke(input_text)

    all_docs = guidance_docs + templates_docs + sars_docs

    context = format_docs(all_docs)

    response = chain.invoke({
        "context": context,
        "question": input_text
    })
    st.write(response)