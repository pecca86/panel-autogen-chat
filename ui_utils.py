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
        pass

    def paint_general_ui(self):
        """
        Paints the general UI where the user can select the social media platform
        """

        def print_platform(event):
            print("HOMO KULLI!")
            if self.general_template is not None:
                self.select_btn.visible = not self.select_btn.visible
                self.twitter_column.visible = not self.twitter_column.visible
                print("adding...")
                self.general_template.main.append(
                    pn.Row(pn.widgets.Button(name="homo btn"))
                )
                self.general_template.main.append(pn.pane.Markdown("# Social Pekka"))

        platform_selector = pn.widgets.Select(
            name="Social Media", options=["Twitter", "LinkedIn"]
        )
        pn.bind(print_platform, platform_selector, watch=True)

        self.select_btn = pn.widgets.Button(name="Select")
        self.select_btn.visible = False

        self.twitter_column = pn.Column(
            pn.pane.Markdown("MUNAT AINA PYSTYS!")
        )
        self.twitter_column.visible = False

        self.general_template = pn.template.FastListTemplate(
            site="Awesome Panel",
            title="Social Media",
            main=[
                pn.Column(
                    pn.pane.Markdown("## Social Media"),
                    pn.pane.PNG(
                        "https://www.gstatic.com/images/branding/product/2x/photos_96dp.png"
                    ),
                    platform_selector,
                    self.select_btn,
                ),
                self.twitter_column
            ],
            header_background="black",
            header_color="white",
        )
        return self.general_template

    def _paint_linked_in_ui(self):
        pass

    def get_twitter_chat(self):
        twitter = Twitter()
        return twitter.get_twitter_chat()

    def get_linked_in_chat(self):
        linkedin = LinkedIn()
        return linkedin.get_linked_in_chat()