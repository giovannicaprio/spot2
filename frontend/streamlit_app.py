import streamlit as st
import requests
import json
import os
from typing import List, Dict
from datetime import datetime
import pandas as pd

# Constants
API_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API_KEY = "12345678901234567890123456789012"  # Replace with your actual API key

def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "collected_fields" not in st.session_state:
        st.session_state.collected_fields = {}
    if "mongodb_documents" not in st.session_state:
        st.session_state.mongodb_documents = []
    if "mongodb_documents_df" not in st.session_state:
        st.session_state.mongodb_documents_df = None
    if "mongodb_collections" not in st.session_state:
        st.session_state.mongodb_collections = []
    if "selected_collection" not in st.session_state:
        st.session_state.selected_collection = "collected_info"

def send_message(message: str) -> Dict:
    """Send message to API and get response."""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            headers={"X-API-Key": API_KEY},
            json={
                "message": message,
                "conversation_history": st.session_state.messages
            }
        )
        
        # Check if the response status code indicates an error
        if response.status_code != 200:
            error_data = response.json()
            error_message = "An error occurred while processing your request."
            
            # Handle specific error cases
            if response.status_code == 401:
                error_message = "Authentication failed. Please check your API key."
            elif "error" in error_data:
                error = error_data["error"]
                if isinstance(error, dict):
                    if error.get("type") == "insufficient_quota":
                        error_message = "Sorry, the service is currently unavailable due to API quota limitations. Please try again later."
                    elif "message" in error:
                        error_message = error["message"]
            
            st.error(error_message)
            return None
            
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to the server at {API_URL}. Please make sure the backend server is running.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return None

def reset_conversation():
    """Reset the conversation."""
    requests.post(f"{API_URL}/reset")
    st.session_state.messages = []
    st.session_state.collected_fields = {}

def fetch_mongodb_collections():
    """Fetch available MongoDB collections."""
    try:
        response = requests.get(
            f"{API_URL}/mongodb/collections",
            headers={"X-API-Key": API_KEY}
        )
        if response.status_code == 200:
            st.session_state.mongodb_collections = response.json()
        else:
            st.error(f"Error fetching MongoDB collections: {response.text}")
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")

def fetch_mongodb_documents(collection_name: str = "collected_info"):
    """Fetch documents from MongoDB."""
    try:
        response = requests.get(
            f"{API_URL}/mongodb/documents/{collection_name}",
            headers={"X-API-Key": API_KEY}
        )
        if response.status_code == 200:
            st.session_state.mongodb_documents = response.json()
            
            # Format documents and create DataFrame
            formatted_docs = [format_document(doc) for doc in st.session_state.mongodb_documents]
            if formatted_docs:
                df = pd.DataFrame(formatted_docs)
                
                # Reorder columns to show important information first
                columns = ["_id", "budget", "total_size", "property_type", "city", "conversation_id", "created_at", "updated_at", "additional_fields"]
                # Only include columns that exist in the DataFrame
                existing_columns = [col for col in columns if col in df.columns]
                df = df[existing_columns]
                
                st.session_state.mongodb_documents_df = df
            else:
                st.session_state.mongodb_documents_df = None
        else:
            st.error(f"Error fetching MongoDB documents: {response.text}")
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")

def format_document(doc: Dict) -> Dict:
    """Format a MongoDB document for display."""
    formatted = doc.copy()
    
    # Format timestamps
    if "created_at" in formatted:
        formatted["created_at"] = datetime.fromisoformat(formatted["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    if "updated_at" in formatted:
        formatted["updated_at"] = datetime.fromisoformat(formatted["updated_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    
    # Format additional fields
    if "additional_fields" in formatted:
        formatted["additional_fields"] = json.dumps(formatted["additional_fields"], indent=2)
    
    return formatted

def display_document_details(doc: Dict):
    """Display detailed information about a document."""
    st.subheader(f"Document ID: {doc['_id']}")
    
    # Create two columns for the layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Basic Information**")
        for field in ["budget", "total_size", "property_type", "city", "conversation_id"]:
            if field in doc:
                st.write(f"**{field}:** {doc[field]}")
    
    with col2:
        st.write("**Timestamps**")
        for field in ["created_at", "updated_at"]:
            if field in doc:
                st.write(f"**{field}:** {doc[field]}")
    
    # Display additional fields
    if "additional_fields" in doc:
        st.write("**Additional Fields**")
        try:
            # Try to parse as JSON if it's a string
            if isinstance(doc["additional_fields"], str):
                additional_fields = json.loads(doc["additional_fields"])
            else:
                additional_fields = doc["additional_fields"]
                
            # Display as a table if it's a dictionary
            if isinstance(additional_fields, dict):
                st.table(pd.DataFrame([additional_fields]))
            else:
                st.json(additional_fields)
        except:
            st.write(doc["additional_fields"])

def main():
    st.title("Spot2 Real Estate Assistant")
    
    # Display backend URL for debugging
    st.sidebar.info(f"Backend URL: {API_URL}")
    
    # Initialize session state
    init_session_state()
    
    # Create tabs
    tab1, tab2 = st.tabs(["Chat", "MongoDB Documents"])
    
    with tab1:
        # Sidebar with collected information
        with st.sidebar:
            st.header("Collected Information")
            for field, value in st.session_state.collected_fields.items():
                st.write(f"**{field}:** {value}")
            
            if st.button("Reset Conversation"):
                reset_conversation()
                st.experimental_rerun()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input
        if prompt := st.chat_input("What are you looking for?"):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get bot response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = send_message(prompt)
                    if response:
                        st.write(response["response"])
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response["response"]}
                        )
                        st.session_state.collected_fields = response["collected_fields"]
                        
                        if response["is_complete"]:
                            st.success("All required information has been collected!")
    
    with tab2:
        st.header("MongoDB Documents")
        
        # Fetch collections if not already fetched
        if not st.session_state.mongodb_collections:
            fetch_mongodb_collections()
        
        # Initialize selected_collection with a default value
        selected_collection = st.session_state.selected_collection
        
        # Collection selector
        if st.session_state.mongodb_collections:
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_collection = st.selectbox(
                    "Select Collection",
                    st.session_state.mongodb_collections,
                    index=st.session_state.mongodb_collections.index(st.session_state.selected_collection) if st.session_state.selected_collection in st.session_state.mongodb_collections else 0
                )
            with col2:
                if st.button("Refresh Documents"):
                    st.session_state.selected_collection = selected_collection
                    fetch_mongodb_documents(selected_collection)
                    st.experimental_rerun()
        
        # Fetch documents if not already fetched or if collection changed
        if selected_collection != st.session_state.selected_collection:
            st.session_state.selected_collection = selected_collection
            fetch_mongodb_documents(selected_collection)
        elif not st.session_state.mongodb_documents:
            fetch_mongodb_documents(selected_collection)
        
        # Display documents
        if st.session_state.mongodb_documents:
            # Show document count
            st.info(f"Total documents: {len(st.session_state.mongodb_documents)}")
            
            # Search functionality
            search_term = st.text_input("Search documents", "")
            
            # Filter DataFrame based on search term
            filtered_df = st.session_state.mongodb_documents_df
            if search_term and filtered_df is not None:
                # Create a mask for each column
                mask = pd.Series(False, index=filtered_df.index)
                for column in filtered_df.columns:
                    # Convert column to string for searching
                    mask = mask | filtered_df[column].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = filtered_df[mask]
            
            # Display the table
            if filtered_df is not None:
                st.dataframe(filtered_df, use_container_width=True)
                
                # Document details
                if len(filtered_df) > 0:
                    st.subheader("Document Details")
                    selected_doc_id = st.selectbox(
                        "Select a document to view details",
                        filtered_df["_id"].tolist()
                    )
                    
                    # Find the selected document
                    selected_doc = next((doc for doc in st.session_state.mongodb_documents if doc["_id"] == selected_doc_id), None)
                    if selected_doc:
                        display_document_details(selected_doc)
            else:
                st.warning("No data available to display")
        else:
            st.info("No documents found. Click 'Refresh Documents' to fetch from MongoDB.")

if __name__ == "__main__":
    main() 