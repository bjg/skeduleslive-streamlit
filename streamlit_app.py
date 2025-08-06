#!/usr/bin/env python3
"""
SkedulesLive MCP Server - Streamlit Web Interface

This script provides a web interface for the SkedulesLive AI Assistant using Streamlit.
"""
import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file for local development
load_dotenv()

# Function to get config values from Streamlit secrets or environment variables
def get_config_value(key, default=None):
    """Get a configuration value from Streamlit secrets or environment variables"""
    # First try to get from Streamlit secrets (for Streamlit Cloud)
    if 'secrets' in dir(st) and key in st.secrets:
        return st.secrets[key]
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)

# OpenAI API Configuration
OPENAI_API_KEY = get_config_value("OPENAI_API_KEY")

# MCP Server Configuration
MCP_SERVER_URL = get_config_value("MCP_SERVER_URL", "http://localhost:8000")
MCP_API_KEY = get_config_value("MCP_API_KEY")

# Import functions from the OpenAI integration script
try:
    from openai_integration import MCP_FUNCTIONS, execute_mcp_function
except ImportError:
    # Define them here as fallback
    from openai_integration import MCP_FUNCTIONS, execute_mcp_function

def chat_with_skeduleslive(user_message):
    """Process a user message with OpenAI and execute any tool calls"""
    
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY environment variable is not set"
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        with st.spinner("AI Assistant is thinking..."):
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an assistant that helps manage SkedulesLive content. You can help create and manage schedules, events, and other content."},
                    {"role": "user", "content": user_message}
                ],
                tools=MCP_FUNCTIONS
            )
        
        # Check if the model wants to call a function
        if response.choices[0].message.tool_calls:
            # Process each tool call
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                st.info(f"Calling SkedulesLive API: {function_name}")
                
                # Execute the function
                with st.spinner(f"Executing {function_name}..."):
                    function_response = execute_mcp_function(function_name, function_args)
                
                st.success(f"API call complete: {function_name}")
                
                # Send the function result back to the model
                with st.spinner("Processing results..."):
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an assistant that helps manage SkedulesLive content. You can help create and manage schedules, events, and other content."},
                            {"role": "user", "content": user_message},
                            {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                            {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(function_response)}
                        ]
                    )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# Streamlit UI
st.set_page_config(
    page_title="SkedulesLive AI Assistant",
    page_icon="📅",
    layout="centered",
)

st.title("📅 SkedulesLive AI Assistant")
st.subheader("Manage your schedules and events with natural language")

# Mode selection toggle
st.sidebar.subheader("App Mode")
if 'use_demo_mode' not in st.session_state:
    st.session_state.use_demo_mode = True
    
use_demo = st.sidebar.checkbox(
    "Use Demo Mode", 
    value=st.session_state.use_demo_mode,
    help="When enabled, uses mock data instead of real API calls"
)

if use_demo != st.session_state.use_demo_mode:
    st.session_state.use_demo_mode = use_demo
    st.experimental_rerun()

# Display current mode
mode_text = "**DEMO MODE**" if st.session_state.use_demo_mode else "**LIVE MODE**"
st.sidebar.markdown(f"Currently using: {mode_text}")

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'auth_tokens' not in st.session_state:
    st.session_state.auth_tokens = None
    
# Authentication UI
with st.sidebar:
    st.header("Authentication")
    
    if not st.session_state.authenticated:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            keep_me_logged = st.checkbox("Keep me logged in", value=True)
            submit = st.form_submit_button("Login")
            
            if submit and email and password:
                # Call the authenticate function
                auth_result = execute_mcp_function(
                    "authenticate",
                    {"email": email, "password": password, "keep_me_logged": keep_me_logged}
                )
                
                if auth_result.get("status") == "success":
                    st.success("Authentication successful!")
                    # Refresh the page to reflect the authenticated state
                    st.experimental_rerun()
                else:
                    st.error(auth_result.get("message", "Authentication failed"))
    else:
        st.success("You are authenticated!")
        if st.button("Logout"):
            st.session_state.authenticated = False
            if 'auth_tokens' in st.session_state:
                del st.session_state.auth_tokens
            st.experimental_rerun()

# Configuration information
with st.sidebar:
    st.header("Configuration")
    
    # MCP Server Status
    st.subheader("MCP Server")
    mcp_status = "🟢 Connected" if MCP_API_KEY else "🔴 Not Configured"
    st.write(f"Status: {mcp_status}")
    st.write(f"URL: {MCP_SERVER_URL}")
    
    # OpenAI Status
    st.subheader("OpenAI")
    openai_status = "🟢 Connected" if OPENAI_API_KEY else "🔴 Not Configured"
    st.write(f"Status: {openai_status}")
    
    st.divider()
    
    # Add some example prompts
    st.subheader("Example Prompts")
    example_prompts = [
        "Show me all my skedules",
        "Create a new skedule for my conference next month",
        "Get events for my tech meetup skedule",
        "What's my user profile information?",
        "Search for skedules about marketing"
    ]
    
    for prompt in example_prompts:
        if st.button(prompt):
            st.session_state.messages.append({"role": "user", "content": prompt})

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("How can I help you with SkedulesLive?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        response = chat_with_skeduleslive(prompt)
        st.markdown(response)
    
    # Add AI response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Configuration warning
if not MCP_API_KEY or not OPENAI_API_KEY:
    st.warning(
        "⚠️ Configuration incomplete. Please set the required environment variables:\n\n"
        "- `MCP_API_KEY`: Your MCP server API key\n"
        "- `OPENAI_API_KEY`: Your OpenAI API key\n"
        "- `MCP_SERVER_URL`: URL to your MCP server"
    )
