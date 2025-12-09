from flask import Flask, render_template
from flask import request, jsonify, abort

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import LLMChain
from langchain_cohere import ChatCohere
from langchain_community.embeddings import CohereEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Initialize Cohere LLM
llm = ChatCohere(cohere_api_key=os.getenv("COHERE_API_KEY"))

# Initialize Memory (stores the last 5 exchanges)
# The memory object should be persistent across requests for a single user/session.
# In a real app, you'd manage session-specific memory. For this starter, we'll use a global one.
memory = ConversationBufferWindowMemory(
    memory_key="chat_history", 
    return_messages=True, 
    k=5
)

# Define Prompt Template
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="You are a helpful and friendly chatbot. Keep your answers concise."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

# Create the Conversational Chain
chatbot_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    memory=memory,
    verbose=True # Set to False in production
)

# --- Knowledge Base Setup ---
# 1. Initialize Embeddings
embeddings = CohereEmbeddings(
        cohere_api_key=os.getenv("COHERE_API_KEY"),
        model="embed-english-light-v2.0",
        user_agent="langchain-chatbot-starter"
    )

# 2. Load the Vector Store (FAISS index)
# This assumes the index has already been created (e.g., from 'README_knowledge_base').
# Replace 'README_knowledge_base' with the actual path if different.
try:
    vectorstore = FAISS.load_local(
        "README_knowledge_base",
        embeddings,
        allow_dangerous_deserialization=True  # <--- ADD THIS PARAMETER
    )
except Exception as e:
    print(f"Error loading vector store: {e}")
    vectorstore = None
    
    
# 3. Create the RAG Chain (RetrievalQA)
if vectorstore:
    kb_chain = RetrievalQA.from_chain_type(
        llm=llm,  # <--- ADD THIS LINE
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        return_source_documents=True
    )
else:
    kb_chain = None

# Define the routing prompt
ROUTER_PROMPT_TEMPLATE = """
You are an intelligent router. Your job is to classify the user's question to determine the best response mechanism.

The classification options are:
1. 'knowledge_base': The question relates directly to the contents of the internal knowledge base (e.g., questions about setting up the application, LangChain components, Cohere, or FAISS).
2. 'general_chat': The question is a general inquiry, greeting, or unrelated to the internal knowledge base.

Respond with ONLY the classification tag.

Question: {input}
Classification:
"""

router_prompt = PromptTemplate(
    template=ROUTER_PROMPT_TEMPLATE,
    input_variables=["input"],
)

# Create the router chain (uses the same 'llm' you defined for US-01)
router_chain = LLMChain(
    llm=llm,
    prompt=router_prompt,
    verbose=True
)

def answer_hybrid(message):
    global router_chain
    
    # 1. Run the router chain to classify the question
    classification = router_chain.run(input=message).strip().lower()

    # 2. Delegate based on classification
    if 'knowledge_base' in classification:
        print("Routing to Knowledge Base...")
        answer, sources = answer_from_knowledgebase(message)
        mode = "Knowledge Base"
    else:
        print("Routing to General Chat...")
        answer = answer_as_chatbot(message) # This function returns only the answer
        sources = "" # General chat has no sources
        mode = "General Chat"
        
    return answer, sources, mode

def answer_from_knowledgebase(message):
    global kb_chain # Ensure kb_chain is accessible if defined later

    if not kb_chain:
        # If the chain isn't initialized (e.g., FAISS load failed), 
        # return a default answer and empty source list.
        return "Knowledge base chain is not initialized. Please check setup and logs.", ""
    
    try:
        # Run the RAG chain
        result = kb_chain({"query": message})
        
        # Extract the answer and sources
        answer = result.get("result", "Answer not found.")
        sources = [doc.metadata.get('source', 'Unknown') for doc in result.get('source_documents', [])]
        
        # Combine the answer and a string of unique sources
        unique_sources_str = ", ".join(sorted(list(set(sources))))
        
        # Return both the answer and the sources
        return answer, unique_sources_str
        
    except Exception as e:
        # If an error occurs during execution, return an error message but still 
        # adhere to the expected return type (two values).
        return f"Error during knowledge base query: {str(e)}", "Error"

def search_knowledgebase(message):
    global kb_chain
    if not kb_chain:
        return "Knowledge base chain is not initialized.", ""
    
    try:
        # Search for relevant documents without invoking the LLM
        # Assuming kb_chain is a RetrievalQA chain, we access its retriever
        docs = kb_chain.retriever.get_relevant_documents(message)
        
        # specific logic to format search results
        if not docs:
            return "No relevant documents found.", ""
            
        answer = "Found the following relevant documents:\n"
        sources = []
        for i, doc in enumerate(docs, 1):
            # Show a snippet of the content
            snippet = doc.page_content[:200].replace('\n', ' ')
            answer += f"\n{i}. {snippet}...\n"
            sources.append(doc.metadata.get('source', 'Unknown'))
            
        unique_sources_str = ", ".join(sorted(list(set(sources))))
        return answer, unique_sources_str
        
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}", ""

def answer_as_chatbot(message):
    # Pass the user message to the chain
    response = chatbot_chain.run(message)
    # The chain automatically handles history via the 'memory' object
    return response

@app.route('/kbanswer', methods=['POST'])
def kbanswer():
    try:
        data = request.json
        message = data.get('message', '')
        
        # Call the knowledge base function
        answer, sources = answer_from_knowledgebase(message)

        # Return the response as JSON
        return jsonify({
            "answer": answer,
            "sources": sources
        })
        
    except Exception as e:
        # Proper error handling
        return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['POST'])
def search():    
    try:
        data = request.json
        message = data.get('message', '')
        
        # Call the hybrid function
        answer, sources, mode = answer_hybrid(message)

        # Return the response as JSON
        return jsonify({
            "answer": answer,
            "sources": sources,
            "mode": mode
        })
        
    except Exception as e:
        # Proper error handling
        return jsonify({"error": str(e)}), 500

@app.route('/answer', methods=['POST'])
def answer():
    try:
        data = request.json
        message = data.get('message', '')
        
        # Call the general chatbot function (US-01)
        response = answer_as_chatbot(message)

        # Return the response as JSON
        return jsonify({
            "answer": response
        })
        
    except Exception as e:
        # Proper error handling
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    mode = data.get('mode', 'chat') # Default to 'chat'

    if mode == "search":
        answer, sources = search_knowledgebase(message)
    elif mode == "rag":
        answer, sources = answer_from_knowledgebase(message)
    else: # Default to 'chat' (Answer as Chatbot)
        answer = answer_as_chatbot(message)
        sources = ""

    return jsonify({"answer": answer, "source": sources})

@app.route("/")
def index():
    return render_template("index.html", title="")

if __name__ == "__main__":
    app.run()