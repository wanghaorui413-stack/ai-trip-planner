import logging
import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# This assumes the script is run in an environment where logging_config.py is available
# Or it will use Python's default basic logging.
logger = logging.getLogger(__name__)


def load_documents_from_folder(folder_path: str) -> List:
    """
    Load and return documents from all supported files in the folder.
    Supported: PDF, TXT, DOCX
    """
    documents = []
    logger.info(f"Scanning folder for documents: {folder_path}")
    if not os.path.exists(folder_path):
        logger.error(f"Knowledge base folder not found at path: {folder_path}")
        return documents

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        ext = filename.split('.')[-1].lower()

        loader = None
        if ext == 'pdf':
            loader = PyPDFLoader(file_path)
        elif ext == 'txt':
            loader = TextLoader(file_path)
        elif ext == 'docx':
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            logger.warning(f"Ignoring unsupported file type: '{filename}'")
            continue

        try:
            logger.info(f"Loading document: '{filename}'")
            docs = loader.load()
            for doc in docs:
                doc.metadata = {"source": filename}
            documents.extend(docs)
        except Exception as e:
            logger.error(f"Failed to load document '{filename}': {e}", exc_info=True)

    logger.info(f"Successfully loaded content from {len(documents)} document(s).")
    return documents

def create_vector_store_from_folder(folder_path: str, store_path: str = "faiss_store") -> FAISS:
    """
    Load documents from folder, chunk, embed, and save to FAISS vector store.
    """
    if os.path.exists(store_path):
        logger.info(f"Vector store already exists at '{store_path}'. Skipping creation.")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return FAISS.load_local(store_path, embeddings, allow_dangerous_deserialization=True)

    logger.info(f"Creating new vector store from documents in '{folder_path}'...")
    docs = load_documents_from_folder(folder_path)

    if not docs:
        logger.warning("No documents were loaded. Vector store will not be created.")
        return

    logger.info(f"Splitting {len(docs)} documents into text chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunked_docs = text_splitter.split_documents(docs)
    logger.info(f"Documents split into {len(chunked_docs)} chunks.")


    logger.info("Initializing embedding model 'all-MiniLM-L6-v2'...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    logger.info("Creating FAISS vector store from chunks and saving to disk...")
    try:
        vector_store = FAISS.from_documents(chunked_docs, embeddings)
        vector_store.save_local(store_path)
        logger.info(f"Vector store successfully created and saved to '{store_path}'.")
        return vector_store
    except Exception as e:
        logger.error(f"Failed to create or save the vector store: {e}", exc_info=True)


if __name__ == "__main__":
    from logging_config import setup_logging

    # Set up our centralized logging when running this script directly
    setup_logging()

    KNOWLEDGE_BASE_DIR = "./knowledge_base"
    logger.info("--- Starting RAG Vector Store Creation Process ---")
    create_vector_store_from_folder(KNOWLEDGE_BASE_DIR)
    logger.info("--- RAG Vector Store Creation Process Finished ---")
