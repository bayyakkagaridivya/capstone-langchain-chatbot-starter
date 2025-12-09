import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import CohereEmbeddings
from langchain_community.vectorstores import FAISS

# Load environment variables (needed for Cohere API Key)
load_dotenv()

# --- Configuration ---
SOURCE_FILE = "README.md"
INDEX_PATH = "README_knowledge_base"
COHERE_MODEL = "embed-english-light-v2.0" # Must match the model in app.py

def create_knowledge_base():
    """
    Loads, splits, embeds, and saves documents to a FAISS vector store.
    """
    print(f"Starting Knowledge Base creation from {SOURCE_FILE}...")
    
    # 1. Load Document
    try:
        loader = TextLoader(SOURCE_FILE)
        documents = loader.load()
    except FileNotFoundError:
        print(f"Error: Source file '{SOURCE_FILE}' not found.")
        return
        
    # 2. Split Document into Chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    texts = text_splitter.split_documents(documents)
    print(f"Split document into {len(texts)} chunks.")

    # 3. Initialize Embeddings (using the same model as in app.py)
    cohere_api_key = os.getenv("COHERE_API_KEY")
    if not cohere_api_key:
        print("Error: COHERE_API_KEY not found. Check your .env file.")
        return

    embeddings = CohereEmbeddings(
        cohere_api_key=cohere_api_key,
        model=COHERE_MODEL,
        user_agent="langchain-chatbot-starter"
    )
    
    # 4. Create and Save the FAISS Vector Store
    print("Generating embeddings and saving to FAISS index. This may take a moment...")
    try:
        vectorstore = FAISS.from_documents(texts, embeddings)
        vectorstore.save_local(INDEX_PATH)
        print(f"\n✅ Success! Knowledge Base saved to directory: {INDEX_PATH}")
    except Exception as e:
        print(f"\n❌ An error occurred during embedding or saving: {e}")

if __name__ == "__main__":
    create_knowledge_base()