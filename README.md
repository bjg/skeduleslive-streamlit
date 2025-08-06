# SkedulesLive MCP Server - Streamlit Interface

This repository contains a Streamlit web interface for the SkedulesLive MCP server, allowing users to interact with SkedulesLive content using natural language through OpenAI's function calling API.

## Files

- `streamlit_app.py` - Main Streamlit application
- `openai_integration.py` - OpenAI function calling integration
- `requirements.txt` - Dependencies
- `.streamlit/config.toml` - Streamlit configuration

## Deployment to Streamlit Cloud

### Step 1: Create a Streamlit Cloud Account
If you don't have one already, create an account at [share.streamlit.io](https://share.streamlit.io).

### Step 2: Connect to GitHub
Connect your Streamlit Cloud account to GitHub and select this repository.

### Step 3: Configure Secrets
In the Streamlit Cloud deployment settings, add the following secrets:

```toml
# .streamlit/secrets.toml
MCP_SERVER_URL = "http://skeduleslive-mcp-alb-1371253899.eu-west-1.elb.amazonaws.com"
MCP_API_KEY = "your_secure_api_key"
OPENAI_API_KEY = "your_openai_api_key"
```

### Step 4: Deploy
Click the "Deploy" button and wait for Streamlit Cloud to build and deploy your app.

## Local Development

To run this app locally:

1. Create a `.env` file with the following variables:
   ```
   MCP_SERVER_URL=http://skeduleslive-mcp-alb-1371253899.eu-west-1.elb.amazonaws.com
   MCP_API_KEY=your_secure_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:
   ```
   streamlit run streamlit_app.py
   ```

## Using the App

Once deployed, you can:
1. Ask questions about your SkedulesLive content
2. Create and manage skedules and events
3. Search for specific content

The app uses OpenAI's function calling API to translate natural language requests into API calls to the MCP server.
