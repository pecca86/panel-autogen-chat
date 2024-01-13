import os
import json
from requests_oauthlib import OAuth1Session
import re
import asyncio
import autogen
from openai import OpenAI
import panel as pn
from info import MyAccordion
import autogen
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from chromadb.utils import embedding_functions
from twitter import Twitter
from linkedin import LinkedIn

pn.extension(notifications=True)



class AppUI:

    general_template = None

    def __init__(self) -> None:
        self.linkedin = LinkedIn()

    def paint_general_ui(self):
        pass

    def _paint_linked_in_ui(self):
        pass

    def get_twitter_chat(self):
        twitter = Twitter()
        return twitter.get_twitter_chat()

    def get_linked_in_chat(self, file_input, agent_temperature):
        return self.linkedin.get_linked_in_chat(file_input, agent_temperature)
    
    def set_rag(self, rag_selected):
        self.linkedin.set_rag(rag_selected)