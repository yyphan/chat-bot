# chat-bot
## Part-1

### Used AIs: 
Gemini for requirement analysis and project planning
Claude Code for coding

### Major Human Inputs:
1. In order to deploy (easily), I researched and picked Streamlit as the frontend framework. But by that time the backend has been set up (by AI), so I had to refactor by calling the backend functions directly from frontent (see `streamlit_app.py`) 
2. In the RAG part where we fetch Q&As from the given link. AI wasn't able to get anything at first, so I investigated ZenDesk's structure and broke it down for it, plus for the deployed version, I feel it is more legit fetching from ZenDesk's own APIs rather than web crawling so made AI do it.

### Features I would have added if I had more time
1. persisted storage for guidelines + reported mistakes + corrections
2. session storage of conversation (at least per browser session)
3. option to transfer to human specialists at certain points during the conversations

### Securities Add-Ons if I had time
1. encryption of user data (e.g. transcation ID, card details)
2. prevent prompt attacks