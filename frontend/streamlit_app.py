import streamlit as st
import requests
import json
from typing import List, Dict

# Constants
API_URL = "http://localhost:8000"
API_KEY = "12345678901234567890123456789012"  # Replace with your actual API key

def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "collected_fields" not in st.session_state:
        st.session_state.collected_fields = {}

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
        st.error("Could not connect to the server. Please make sure the backend server is running.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return None

def reset_conversation():
    """Reset the conversation."""
    requests.post(f"{API_URL}/reset")
    st.session_state.messages = []
    st.session_state.collected_fields = {}

def main():
    st.title("Spot2 Real Estate Assistant")
    
    # Initialize session state
    init_session_state()
    
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

if __name__ == "__main__":
    main() 