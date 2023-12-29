import autogen
import openai
from openai import OpenAI
import panel as pn
import json
from requests_oauthlib import OAuth1Session
import subprocess
from info import MyAccordion

import os
import time
import re
import asyncio
import sys
import threading
pn.extension(notifications=True)

input_future = None

## LOAD SPINNER
indicator = pn.indicators.LoadingSpinner(value=False, size=25, styles={'margin-left': '10.5rem'})
selected_post_text = None
is_post_selected = False
post_draft_initialized = False
initiate_chat_task_created = False
final_image_prompt = None
original_image_prompt = None

# AGENTS
user_proxy = None
question_agent = None
question_agent_name = None
linkedin_agent = None
linkedin_agent_name = None
critic_agent = None
critic_agent_name = None
seo_critic_agent = None
seo_critic_agent_name = None
image_agent = None
image_agent_name = None
groupchat = None
manager = None
avatar = None


def setup():
    main()
    
def main():
    config_list = [
            {
                "model": "gpt-4-1106-preview",
                "api_key": os.getenv("OPENAI_API_KEY"),
            }
        ]
    gpt4_config = {"config_list": config_list, "temperature":0, "seed": 53}

    ###### A G E N T  F U N C T I O N S #########
    def call_dalle(prompt) -> str:
        dall_e_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        response = dall_e_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        print(f"Image url: {image_url}")
        return image_url
    
    def init_agents():
        global user_proxy
        global question_agent
        global question_agent_name
        global linkedin_agent
        global linkedin_agent_name
        global critic_agent
        global critic_agent_name
        global seo_critic_agent
        global seo_critic_agent_name
        global image_agent
        global image_agent_name
        global groupchat
        global manager
        global avatar

        class MyConversableAgent(autogen.ConversableAgent):
            global user_proxy
            global question_agent
            global question_agent_name
            global linkedin_agent
            global linkedin_agent_name
            global critic_agent
            global critic_agent_name
            global seo_critic_agent
            global seo_critic_agent_name
            global image_agent
            global image_agent_name
            global groupchat
            global manager

            def continue_chat(self, event):
                global is_post_selected
                global indicator

                if event is None:
                    return
                indicator.value = True
                is_post_selected = True
                input_future.set_result("good!")
                manager.send(selected_post_text, image_agent, request_reply=False, silent=True)
                groupchat.agents.append(image_agent)

            async def a_get_human_input(self, prompt: str) -> str:
                global input_future
                global is_post_selected
                global indicator
                
                indicator.value = False

                # prompt = Provide feedback to chat_manager. Press enter to skip and use auto-reply, or type 'exit' to end the conversation:
                # chat_interface.send(prompt, user="System", respond=False)
                if not is_post_selected and post_draft_initialized:
                    feedback_button = pn.widgets.Button(name='Use this draft!', button_type='primary')
                    pn.bind(self.continue_chat, feedback_button, watch=True)
                    chat_interface.send(pn.Row(feedback_button), user="System", respond=False)
                    chat_interface.send("Give feedback in the chat to generate a new draft. Otherwise click the 'use this draft' button.", user="System", respond=False)
                # Create a new Future object for this input operation if none exists
                if input_future is None or input_future.done():
                    input_future = asyncio.Future()

                # Wait for the callback to set a result on the future
                await input_future

                # Once the result is set, extract the value and reset the future for the next input operation
                input_value = input_future.result()
                input_future = None
                return input_value

        ###### A G E N T S #########
        user_proxy = MyConversableAgent(
        name="Admin",
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
        system_message="""A human admin. First interact with the question_agent to outline what type of LinkedIn post you want to create. Then interact with the linkedin_agent to discuss the linkedin post. Prompt needs to be approved by this admin. 
        """,
        code_execution_config=False,
        human_input_mode="ALWAYS",
        )
        question_agent_name = "question_agent"
        question_agent = autogen.AssistantAgent(
            name=question_agent_name,
            system_message="""You are the question_agent. You will begin the conversation by asking the Admin, one question a time, the following questions:
            1. What sort of post are you aiming to create? (e.g, Humorous, Business, Serious, Quirky)
            2. Who is your target audience? (e.g, B2B, B2C, Business, Casual Reader, Partner)
            3. What should the tone of voice be? (e.g, Formal, Informal, Casual, Friendly, Authoritative)
            You will ALWAYS wait for the Admin response before asking the next question or proceeding to the next agent.
            In the end summarize all the information and send it to the linkedin_agent.
            """
        )
        linkedin_agent_name = "linkedin_agent"
        linkedin_agent = autogen.AssistantAgent(
            name=linkedin_agent_name,
            system_message="""Create a LinkedIn post based on the Admin message and the base questions asked by the question_agent. Structure the post in the following way:
            1. Title
            2. Body
            You will iterate with the critic_agent to improve the tweet based on the critic_agents and the seo_critic_agent feedback. You will stop and wait for Admin feedback once you get a score of 4/5 or above.
            """,
            llm_config={
                "config_list": config_list,
                "temperature": 0.5,
                "frequency_penalty": 0.1,
            }
        )
        critic_agent_name = "critic_agent"
        criteria_list = ["grammar", "clarity", "conciseness", "originality", "humor", "emotion", "relevance", "overall"]
        critic_agent = autogen.AssistantAgent(
            name=critic_agent_name,
            system_message=f"You are the critic_agent. You will provide feedback to the linked_in on how to improve the linked in post. You will provide feedback on the following critera {criteria_list}. The post is good when the score is a minumum of 4/5. Also take into account the Admin's feedback!",
            llm_config={
                "config_list": config_list,
                "temperature": 0,
                "frequency_penalty": 0,
            }
        )
        seo_critic_agent_name = "seo_critic_agent"
        seo_critic_agent = autogen.AssistantAgent(
            name=seo_critic_agent_name,
            system_message=f"""You are an SEO expert who will provide SEO related feedback to the linkedin_agent. The feedback will be based on these criteria by scoring 0 to 5:
            * Use relevant keywords in your title. The title is one of the most important factors for visibility and rankings. Include 2-3 relevant keywords or phrases.
            * Include keywords naturally in the first paragraph. This text is sometimes indexed by search engines, so work keywords into the introduction.
            * Include relevant hashtags. Add 2-3 hashtags related to your industry, topic, location, etc. to expand reach.
            * Write for readers, not just bots. SEO is important but high-quality, human-focused content performs best overall.
            * Promote comments and shares. Engage your network to boost social signals and page Authority over time.
            """,
            llm_config={
                "config_list": config_list,
                "temperature": 0,
                "frequency_penalty": 0,
            }
        )
        image_agent_name = "image_agent"
        image_agent = autogen.AssistantAgent(
            name=image_agent_name,
            system_message="create a prompt for dall-e 3 based on the title by in the publisher_agent message. The prompt should be short and descriptive. Iterate on the prompt based on the Admin's feedback. THIS AGENT WILL RUN LAST!",
            llm_config={
                "config_list": config_list,
                "temperature": 0.5,
                "frequency_penalty": 0.1,
            }
        )

        user_proxy.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        )
        question_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )
        linkedin_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )
        critic_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )
        seo_critic_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )
        image_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )

        #### G R O U P C H A T #####
        groupchat = autogen.GroupChat(agents=[user_proxy, question_agent, linkedin_agent, critic_agent, seo_critic_agent], messages=[], max_round=20)
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

        avatar = {user_proxy.name:"👨‍💼", question_agent.name:"👨‍🔧", linkedin_agent.name:"👩‍💻", critic_agent.name:"👨‍🏫", seo_critic_agent.name:"🤖", image_agent.name:"🌈", "call_dalle": "🪄"}

    ####### COMPONENT FUNCTIONS ########
    def edit_prompt(prompt_input):
        global final_image_prompt
        final_image_prompt = prompt_input

    def post_to_dall_e(event):
        global final_image_prompt
      
        def no_clicked(event):
            image_prompt = pn.widgets.TextAreaInput(
                auto_grow=True, 
                max_rows=30,
                rows=5, 
                value=final_image_prompt, 
                name="Image Prompt",
                width=1100,
                height=150
            )
            pn.bind(edit_prompt, prompt_input=image_prompt, watch=True)
            chat_interface.send("Edit the prompt / keep the generated prompt. Click the 'Create Image' button to generate the image. Otherwise provide feedback in the chat to generate a new prompt.", user="System", respond=False)

            button = pn.widgets.Button(name='Create Image', button_type='primary')
            pn.bind(post_to_dall_e, button, watch=True)

            chat_interface.send(pn.Column(image_prompt, button), user="System", respond=False)

        def yes_clicked(events):
            input_future.cancel()
            chat_interface.disabled = True
            chat_interface.send("Task completed. You can now close this page. If you want to re-run the program, please refresh the page! 🙂", user="System", respond=False)

        if not event:
            return
        if final_image_prompt is None:
            final_image_prompt = original_image_prompt
        chat_interface.send(f"Generating image with the prompt: ```{final_image_prompt}```", user="System", respond=False)
        image_url = call_dalle(final_image_prompt)
        chat_interface.send(image_url, user="System", respond=False)

        ### CHECK IF USER IS HAPPY WITH THE IMAGE ###
        chat_interface.send("Are you happy with the image?", user="System", respond=False)       
        yes_button = pn.widgets.Button(name='Yes', button_type='primary')
        no_button  = pn.widgets.Button(name='No', button_type='primary')
        pn.bind(yes_clicked, yes_button, watch=True)
        pn.bind(no_clicked, no_button, watch=True)
        chat_interface.send(pn.Row(yes_button, no_button), user="System", respond=False)

    def print_messages(recipient, messages, sender, config):
        global indicator

        print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

        if all(key in messages[-1] for key in ['name']):
            global final_image_prompt
            global original_image_prompt
            global selected_post_text
            global post_draft_initialized

            original_image_prompt = messages[-1]['content']

            print("SENDER NAME: ", messages[-1]['name'])

            #TESTING: Don't echo the User message as Admin
            if messages[-1]['name'] != user_proxy.name:
                chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
            indicator.value = True

            if messages[-1]['name'] == linkedin_agent_name:
                post_draft_initialized = True
                selected_post_text = messages[-1]['content']

            if messages[-1]['name'] == image_agent_name or messages[-1]['name'] == "image_agent":
                print("Image agent message received")
                # encapsulate into a function
                image_prompt = pn.widgets.TextAreaInput(
                    auto_grow=True, 
                    max_rows=30,
                    rows=5, 
                    value=messages[-1]['content'], 
                    name="Image Prompt",
                    width=1100,
                    height=150
                )
                pn.bind(edit_prompt, prompt_input=image_prompt, watch=True)

                button = pn.widgets.Button(name='Create Image', button_type='primary')
                pn.bind(post_to_dall_e, button, watch=True)
                
                chat_interface.send(pn.Column(image_prompt, button), user="System", respond=False)

                chat_interface.send("Edit the prompt / keep the generated prompt. Click the 'Create Image' button to generate the image. Otherwise provide feedback in the chat to generate a new prompt.", user="System", respond=False)
        else:
            return False, None  # required to ensure the agent communication flow continues
        
        return False, None  # required to ensure the agent communication flow continues


    pn.extension(design="material")

    async def delayed_initiate_chat(agent, recipient, message):

        global initiate_chat_task_created
        # Indicate that the task has been created
        initiate_chat_task_created = True

        # Wait for 2 seconds
        await asyncio.sleep(0.5)

        # Now initiate the chat   
        await agent.a_initiate_chat(recipient, message=message)

    async def callback(contents: str, user: str, instance: pn.chat.ChatInterface):
        
        global initiate_chat_task_created
        global input_future
        global indicator

        if not initiate_chat_task_created:
            print("Creating task...")
            if os.getenv("OPENAI_API_KEY") is None:
                print("MULKKU")
                chat_interface.send("Please enter you OpenAI key to begin the chat!", user="System", respond=False)
                return
            init_agents()
            asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))
        else:
            if input_future and not input_future.done():
                input_future.set_result(contents)
            else:
                print("No more messages awaited...")

    ### G U I  C O M P O N E N T S #####
    def add_openai_key_to_env(key): 
        SYSTEM_KWARGS = dict(
            user="System",
            respond=False,
        )
        if not key.startswith("sk-"):
            chat_interface.send("Please enter a valid OpenAI key!", **SYSTEM_KWARGS)
            return

        os.environ["OPENAI_API_KEY"] = key
        chat_interface.clear()
        chat_interface.send("Give a short description on the LinkedIn Post you wish to create 🙂", user="System", respond=False)
        chat_interface.disabled = False

    # MAIN COMPONENTS
    chat_interface = pn.chat.ChatInterface(callback=callback)
    chat_interface.disabled = True
    # Chat buttons
    chat_interface.show_rerun = False
    chat_interface.show_undo = False

    ### COMPONENT FUNCTIONS ###
    def set_max_inputs(max_inputs):
        print(max_inputs)

    # COLUMN COMPONENTS
    api_key_input = None
    if os.environ.get("OPENAI_API_KEY") is None:
        chat_interface.send("Please enter you OpenAI key to begin the chat!", user="System", respond=False)
        api_key_input = pn.widgets.PasswordInput(placeholder="sk-...", name="OpenAI Key")
        pn.bind(add_openai_key_to_env, key=api_key_input, watch=True)
    else:
        chat_interface.disabled = False
        chat_interface.send("Give a short description on the LinkedIn Post you wish to create 🙂", user="System", respond=False)

    flow_selector = pn.widgets.Select(options=['Twitter', 'LinkedIn', 'Instagram', 'Facebook', 'Web Page'], name='Target Platform')
    temp_slider = pn.widgets.FloatSlider(name='Temperature', start=0, end=1, value=0.5)
    freq_slider = pn.widgets.FloatSlider(name='Frequency Penalty', start=0, end=1, value=0.5)
    max_rounds_input = pn.widgets.IntInput(name='Max Rounds', value=20, start=1, end=30, step=1)
    pn.bind(set_max_inputs, max_inputs=max_rounds_input, watch=True)
    type_of_post_selector = pn.widgets.Select(options=['Humorous', 'Business', 'Serious', 'Quirky'], name='Type of Post')
    target_audience_selector = pn.widgets.Select(options=['B2B', 'B2C', 'Business', 'Casual Reader', 'Partner'], name='Target Audience')
    file_input = pn.widgets.FileInput(accept='.csv,.json,.pdf')

    column = pn.Column('Settings', api_key_input, flow_selector, temp_slider, freq_slider, max_rounds_input, type_of_post_selector, target_audience_selector, file_input)

    info_accordion = MyAccordion.get_accordion()

    logout = pn.widgets.Button(name="Log out")
    logout.js_on_click(code="""window.location.href = './logout'""")
    # PANEL
    template = pn.template.MaterialTemplate(
        title="Autogen Chat",
        header=[info_accordion, indicator],
        sidebar=[logout, column],
        main=[chat_interface],
    )

    template.servable()
    # template.show()

if __name__ == "__main__":
    # main()
    setup()

setup()
