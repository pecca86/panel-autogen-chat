import os
import json
import sys
from requests_oauthlib import OAuth1Session
import re
import asyncio
import autogen
import panel as pn
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from IPython.display import Image
import yfinance as yf

pn.extension(notifications=True)

input_future = None


class DocumentWizard:
    chat_interface = None

    def __init__(self):
        self.initiate_chat_task_created = False
        self.posted = False
        self.input_future = None

        self.config_list = [
            {
                "model": "gpt-4-1106-preview",
                "api_key": os.getenv("OPENAI_API_KEY"),
            }
        ]
        self.llm_config = {
            "config_list": self.config_list,
            "temperature": 0.1,
            "frequency_penalty": 0.1,
        }

    def check_if_plot_exist_and_send_to_chat(self):
        print("Checking if plot exists")
        if os.path.exists('.groupchat/new_plot.png'):
            print("Plot exists")
            self.chat_interface.send(file='.groupchatnew_plot.png', user='System', respond=False)
            # os.remove('new_plot.png')

    def get_document_wizard_chat(self):
        pn.extension()
        self.tweet_content = None

        class MyConversableAgent(autogen.ConversableAgent):
            chat_interface = None

            def set_input_future(self, input_future):
                self.input_future = input_future

            def set_chat_interface(self, chat_interface):
                self.chat_interface = chat_interface

            async def a_get_human_input(self, prompt: str) -> str:
                self.chat_interface.send(prompt, user="System", respond=False)

                if self.input_future is None or self.input_future.done():
                    self.input_future = asyncio.Future()

                # Wait for the callback to set a result on the future
                await self.input_future

                # Once the result is set, extract the value and reset the future for the next input operation
                input_value = self.input_future.result()
                self.input_future = None
                return input_value

        user_proxy = MyConversableAgent(
            name="User_proxy",
            system_message="A human admin.",
            code_execution_config={
                "last_n_messages": 3,
                "work_dir": "groupchat",
                "use_docker": False,
            },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
            human_input_mode="NEVER",
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE")
        )
        coder = autogen.AssistantAgent(
            name="Coder",  # the default assistant agent is capable of solving problems with code
            llm_config=self.llm_config,
            system_message="You are the coder and tasked with writing python code to solve the task given by the user agent. You will iterate with the Critic until the code is executed successfully. Save the plot to a file name 'new_plot.png'. When done reply TERMINATE."
        )
        critic = autogen.AssistantAgent(
            name="Critic",
            system_message="""Critic. You are a helpful assistant highly skilled in evaluating the quality of a given visualization code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER VISUALIZATION BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the code across the following dimensions
        - bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
        - Data transformation (transformation): Is the data transformed appropriately for the visualization type? E.g., is the dataset appropriated filtered, aggregated, or grouped  if needed? If a date field is used, is the date field first converted to a date object etc?
        - Goal compliance (compliance): how well the code meets the specified visualization goals?
        - Visualization type (type): CONSIDERING BEST PRACTICES, is the visualization type appropriate for the data and intent? Is there a visualization type that would be more effective in conveying insights? If a different visualization type is more appropriate, the score MUST BE LESS THAN 5.
        - Data encoding (encoding): Is the data encoded appropriately for the visualization type?
        - aesthetics (aesthetics): Are the aesthetics of the visualization appropriate for the visualization type and the data?

        YOU MUST PROVIDE A SCORE for each of the above dimensions.
        {bugs: 0, transformation: 0, compliance: 0, type: 0, encoding: 0, aesthetics: 0}
        Do not suggest code.
        Finally, based on the critique above, suggest a concrete list of actions that the coder should take to improve the code.
        """,
            llm_config=self.llm_config,
        )

        groupchat = autogen.GroupChat(
            agents=[user_proxy, coder, critic], messages=[], max_round=20
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=self.llm_config, code_execution_config=False)

        avatar = {user_proxy.name: "😎", coder.name: "🤓", critic.name: "🙄"}

        def print_messages(recipient, messages, sender, config):
            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

            if all(key in messages[-1] for key in ['name']):
                # Don't echo the User message as Admin in the chat interface
                if messages[-1]['name'] != user_proxy.name:
                    self.chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
            else:
                self.chat_interface.send(messages[-1]['content'], user='System', avatar='🥷', respond=False)
                if os.path.exists('./groupchat/new_plot.png'):
                        print("Plot exists")
                        self.chat_interface.send('./groupchat/new_plot.png', user='System', respond=False)
            
            return False, None  # required to ensure the agent communication flow continues

        user_proxy.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )

        coder.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )

        critic.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )

        pn.extension(design="material")

        async def delayed_initiate_chat(agent, recipient, message):
            # Indicate that the task has been created
            self.initiate_chat_task_created = True

            # Wait for 2 seconds
            await asyncio.sleep(2)

            # Now initiate the chat
            await agent.a_initiate_chat(recipient, message=message)

        async def callback(contents: str, user: str, instance: pn.chat.ChatInterface):                
            if not self.initiate_chat_task_created:
                asyncio.create_task(
                    delayed_initiate_chat(user_proxy, manager, contents)
                )

            else:
                if self.input_future and not self.input_future.done():
                    self.input_future.set_result(contents)
                else:
                    if os.path.exists('./groupchat/new_plot.png'):
                        print("Plot exists")
                        self.chat_interface.send('./groupchat/new_plot.png', user='System', respond=False)
                    self.chat_interface.send(
                        "Please refresh the browser to create a new chat session!",
                        user="System",
                        respond=False,
                    )
                    self.chat_interface.disabled = True

        def print_about(instance, event):
            instance.send(
                """This is the document wizard, meant for analyzing documents for statistical purposes.
                          """,
                respond=False,
                user="System",
            )

        self.chat_interface = pn.chat.ChatInterface(
            callback=callback,
            button_properties={
                "about": {"callback": print_about, "icon": "help"},
            },
            widgets=[pn.widgets.TextAreaInput(name="Message", value="")],
        )
        self.chat_interface.show_rerun = False
        self.chat_interface.show_undo = False

        user_proxy.set_chat_interface(self.chat_interface)
        return self.chat_interface
