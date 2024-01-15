import os
import asyncio
import panel as pn
from openai import OpenAI
import autogen
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

pn.extension(notifications=True)

indicator = pn.indicators.LoadingSpinner(value=False, size=25, styles={'margin-left': '10.5rem'}) # load spinner

class LinkedIn:
    
    def __init__(self):
        self.rag_selected = False
        self.input_future = None
        self.initiate_chat_task_created = False
        self.chat_interface = None

        # AGENT SPECIFIC INITS
        self.linkedin_agent_temperature = 0.5
        self.ragproxyagent = None
        self.rag_assistant = None
        self.user_proxy = None
        self.linkedin_agent = None
        self.linkedin_agent_name = None
        self.critic_agent = None
        self.critic_agent_name = None
        self.seo_critic_agent = None
        self.seo_critic_agent_name = None
        self.image_agent = None
        self.image_agent_name = None
        self.groupchat = None
        self.manager = None
        self.avatar = None

        # MISC
        self.msg_count = 0
        self.specifications = {
            "description": "",
            "target_audience": "",
            "type_of_post": "",
            "tone_of_voice": "",
            "rag_prompt": ""
        }
        self.selected_post_text = None
        self.is_post_selected = False
        self.post_draft_initialized = False
        self.final_image_prompt = None
        self.original_image_prompt = None
        self.create_image_btn = pn.widgets.Button(name='Create Image', button_type='primary')

        # UI /
        self.file_name = ""

    def set_rag(self, rag_selected):
        print("RAG SELECTED: ", rag_selected)
        self.rag_selected = rag_selected

    def get_linked_in_chat(self, file_input, agent_temperature):
        # self.rag_selected = rag_selected

        self.agent_temp = agent_temperature
        
        print("INSIDE LINKEDIN CHAT", self.rag_selected)
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
            class MyConversableAgent(autogen.ConversableAgent):

                is_post_selected = False

                feedback_button = pn.widgets.Button(name='Use this draft!', button_type='primary')

                def set_input_future(self, input_future):
                    self.input_future = input_future

                def set_manager(self, manager):
                    self.manager = manager
                
                def set_groupchat(self, groupchat):
                    self.groupchat = groupchat
                
                def set_chat_interface(self, chat_interface):
                    self.chat_interface = chat_interface

                def set_image_agent(self, image_agent):
                    self.image_agent = image_agent

                def set_post_draft_initialized(self, post_draft_initialized):
                    self.post_draft_initialized = post_draft_initialized
                
                def set_selected_post_text(self, selected_post_text):
                    self.selected_post_text = selected_post_text
                
                def continue_chat(self, event):
                    global indicator

                    if event is None:
                        return
                    self.feedback_button.disabled = True
                    self.chat_interface.send("Please wait for the image agent to generate a prompt for the image, this can take a while...", user="System", respond=False)
                    indicator.value = True
                    self.is_post_selected = True
                    self.input_future.set_result("good!")
                    self.manager.send(self.selected_post_text, self.image_agent, request_reply=False, silent=True)
                    self.groupchat.agents.append(self.image_agent)

                async def a_get_human_input(self, prompt: str) -> str:
                    global indicator
                    
                    indicator.value = False

                    if not self.is_post_selected and self.post_draft_initialized:
                        self.feedback_button.disabled = False
                        pn.bind(self.continue_chat, self.feedback_button, watch=True)
                        self.chat_interface.send(pn.Row(self.feedback_button), user="System", respond=False)
                        self.chat_interface.send("Give feedback in the chat to generate a new draft. Otherwise click the 'use this draft' button.", user="System", respond=False)
                    # Create a new Future object for this input operation if none exists
                    if self.input_future is None or self.input_future.done():
                        self.input_future = asyncio.Future()

                    # Wait for the callback to set a result on the future
                    await self.input_future

                    # Once the result is set, extract the value and reset the future for the next input operation
                    input_value = self.input_future.result()
                    self.input_future = None
                    return input_value

            ###### A G E N T S #########
            self.rag_assistant = RetrieveAssistantAgent(
                name="rag_assistant",
                system_message="You are a helpful assistant. You will receive data from the ragproxyagent and provide it to the linkedin_agent.",
                llm_config={
                    "config_list": config_list,
                    "temperature": 0.1,
                    "frequency_penalty": 0.1,
                },
            )
            
            self.ragproxyagent = RetrieveUserProxyAgent(
                name="ragproxyagent",
                system_message="You are the ragproxyagent. You will retrieve content for the rag_assistant to analyze.",
                human_input_mode="NEVER",
                # human_input_mode="TERMINATE",
                retrieve_config={
                    "task": "qa",
                    "docs_path": f"./uploaded_files/{self.file_name}",
                    # "embedding_function": embedding_functions.OpenAIEmbeddingFunction(
                    #     api_key=os.getenv("OPENAI_API_KEY"),
                    #     model_name="text-embedding-ada-002",
                    # )
                },
            )    
            self.ragproxyagent._get_or_create = True
            self.user_proxy = MyConversableAgent(
                name="Admin",
                is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
                system_message="""A human admin that interacts with the linkedin_agent to discuss the linkedin post. Prompt needs to be approved by this admin. 
                """,
                code_execution_config=False,
                human_input_mode="ALWAYS",
            )
            self.user_proxy.set_input_future(self.input_future)
            self.user_proxy.set_chat_interface(self.chat_interface)

            self.linkedin_agent_name = "linkedin_agent"
            self.linkedin_agent = autogen.AssistantAgent(
                name=self.linkedin_agent_name,
                system_message=f"""Create a LinkedIn post based on the input given by the rag_assistant and the following description: {self.specifications['description']}, with the target audience: {self.specifications['target_audience']}, type of post: {self.specifications['type_of_post']} and tone of voice: {self.specifications['tone_of_voice']}. Structure the post in the following way:
                1. Title
                2. Body
                You will iterate with the critic_agent to improve the tweet based on the critic_agents and the seo_critic_agent feedback. You will stop and wait for Admin feedback once you get a score of 4/5 or above.
                """,
                llm_config={
                    "config_list": config_list,
                    "temperature": self.agent_temp,
                    "frequency_penalty": 0.1,
                }
            )
            self.critic_agent_name = "critic_agent"
            criteria_list = ["grammar", "clarity", "conciseness", "originality", "humor", "emotion", "relevance", "overall"]
            self.critic_agent = autogen.AssistantAgent(
                name=self.critic_agent_name,
                system_message=f"You are the critic_agent. You will provide feedback to the linked_in on how to improve the linked in post. You will provide feedback on the following critera {criteria_list}. The post is good when the score is a minumum of 4/5. Also take into account the Admin's feedback!",
                llm_config={
                    "config_list": config_list,
                    "temperature": 0,
                    "frequency_penalty": 0,
                }
            )
            self.seo_critic_agent_name = "seo_critic_agent"
            self.seo_critic_agent = autogen.AssistantAgent(
                name=self.seo_critic_agent_name,
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
            self.image_agent_name = "image_agent"
            self.image_agent = autogen.AssistantAgent(
                name=self.image_agent_name,
                system_message="create a prompt for dall-e 3 based on the title by in the publisher_agent message. The prompt should be short and descriptive. Iterate on the prompt based on the Admin's feedback. THIS AGENT WILL RUN LAST!",
                llm_config={
                    "config_list": config_list,
                    "temperature": 0.5,
                    "frequency_penalty": 0.1,
                }
            )
            self.user_proxy.set_image_agent(self.image_agent)

            self.ragproxyagent.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages, 
                config={"callback": None},
            )
            self.rag_assistant.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages, 
                config={"callback": None},
            )
            self.user_proxy.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages, 
                config={"callback": None},
            )
            self.linkedin_agent.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages,
                config={"callback": None},
            )
            self.critic_agent.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages,
                config={"callback": None},
            )
            self.seo_critic_agent.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages,
                config={"callback": None},
            )
            self.image_agent.register_reply(
                [autogen.Agent, None],
                reply_func=print_messages,
                config={"callback": None},
            )

            #### G R O U P C H A T #####
            if self.rag_selected and file_input.value is not None:
                self.groupchat = autogen.GroupChat(agents=[self.ragproxyagent, self.rag_assistant, self.user_proxy, self.linkedin_agent, self.critic_agent, self.seo_critic_agent], messages=[], max_round=20)
                self.user_proxy.set_groupchat(self.groupchat)
            else:
                self.groupchat = autogen.GroupChat(agents=[self.user_proxy, self.linkedin_agent,self.critic_agent, self.seo_critic_agent], messages=[], max_round=20)
                self.user_proxy.set_groupchat(self.groupchat)

            self.manager = autogen.GroupChatManager(groupchat=self.groupchat, llm_config=gpt4_config)
            self.user_proxy.set_manager(self.manager)

            self.avatar = {self.ragproxyagent.name:"🧠", self.rag_assistant.name:"👽", self.user_proxy.name:"👨‍💼", self.linkedin_agent.name:"👩‍💻", self.critic_agent.name:"👨‍🏫", self.seo_critic_agent.name:"🤖", self.image_agent.name:"🌈", "call_dalle": "🪄"}

        ####### COMPONENT FUNCTIONS ########
        def edit_prompt(prompt_input):
            self.final_image_prompt = prompt_input

        def post_to_dall_e(event):

            self.create_image_btn.disabled = True
        
            def no_clicked(event):
                yes_button.disabled = True
                no_button.disabled = True
                image_prompt = pn.widgets.TextAreaInput(
                    auto_grow=True, 
                    max_rows=30,
                    rows=5, 
                    value=self.final_image_prompt, 
                    name="Image Prompt",
                    width=1100,
                    height=150
                )
                pn.bind(edit_prompt, prompt_input=image_prompt, watch=True)
                self.chat_interface.send("Edit the prompt / keep the generated prompt. Click the 'Create Image' button to generate the image. Otherwise provide feedback in the chat to generate a new prompt.", user="System", respond=False)

                self.create_image_btn = pn.widgets.Button(name='Create Image', button_type='primary')
                pn.bind(post_to_dall_e, self.create_image_btn, watch=True)

                self.chat_interface.send(pn.Column(image_prompt, self.create_image_btn), user="System", respond=False)

            def yes_clicked(events):
                yes_button.disabled = True
                no_button.disabled = True
                self.create_image_btn.disabled = True
                if self.input_future is not None:
                    self.input_future.cancel()
                self.chat_interface.disabled = True
                self.chat_interface.send("Task completed. You can now close this page. If you want to re-run the program, please refresh the page! 🙂", user="System", respond=False)

            if not event:
                return
            if self.final_image_prompt is None:
                self.final_image_prompt = self.original_image_prompt
            self.chat_interface.send(f"Generating image with the prompt: ```{self.final_image_prompt}```", user="System", respond=False)
            image_url = call_dalle(self.final_image_prompt)
            self.chat_interface.send(image_url, user="System", respond=False)

            ### CHECK IF USER IS HAPPY WITH THE IMAGE ###
            self.chat_interface.send("Are you happy with the image?", user="System", respond=False)       
            yes_button = pn.widgets.Button(name='Yes', button_type='primary')
            no_button  = pn.widgets.Button(name='No', button_type='primary')
            pn.bind(yes_clicked, yes_button, watch=True)
            pn.bind(no_clicked, no_button, watch=True)
            self.chat_interface.send(pn.Row(yes_button, no_button), user="System", respond=False)

        def print_messages(recipient, messages, sender, config):
            global indicator

            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

            if all(key in messages[-1] for key in ['name']):

                self.original_image_prompt = messages[-1]['content']

                print("SENDER NAME: ", messages[-1]['name'])

                if messages[-1]['name'] == "ragproxyagent":
                    self.chat_interface.send("Waiting for the rag_assistant to analyze the data...", user="System", respond=False)
                    return False, None

                # Don't echo the User message as Admin in the chat interface
                if messages[-1]['name'] != self.user_proxy.name:
                    self.chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=self.avatar[messages[-1]['name']], respond=False)
                indicator.value = True

                if messages[-1]['name'] == self.linkedin_agent_name:
                    # self.post_draft_initialized = True
                    self.user_proxy.set_post_draft_initialized(True)
                    # self.selected_post_text = messages[-1]['content']
                    self.user_proxy.set_selected_post_text(messages[-1]['content'])

                # IMAGE PROMPT MESSAGE
                if messages[-1]['name'] == "image_agent":
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

                    self.create_image_btn = pn.widgets.Button(name='Create Image', button_type='primary')
                    pn.bind(post_to_dall_e, self.create_image_btn, watch=True)
                    self.chat_interface.send(pn.Column(image_prompt, self.create_image_btn), user="System", respond=False)

                    self.chat_interface.send("Edit the prompt / keep the generated prompt. Click the 'Create Image' button to generate the image. Otherwise provide feedback in the chat to generate a new prompt.", user="System", respond=False)
            else:
                return False, None  # required to ensure the agent communication flow continues
            return False, None  # required to ensure the agent communication flow continues


        pn.extension(design="material")

        async def delayed_initiate_chat(agent, recipient, message):

            # Indicate that the task has been created
            self.initiate_chat_task_created = True

            # Wait for 2 seconds
            await asyncio.sleep(0.5)

            # Now initiate the chat   
            # In Autogen the RagProxyAgent has the key 'problem' for the first prompt compared to 'message' for UserProxyAgent
            if self.rag_selected and file_input.value is not None:
                await agent.a_initiate_chat(recipient, problem=message) 
            else:
                await agent.a_initiate_chat(recipient, message=message)
        
        # inital questions of the chat
        def base_questions(contents, msg_count):
            if msg_count == 0:
                self.chat_interface.send("What is the target audience of the post?", user="System", respond=False)
            elif msg_count == 1:
                self.chat_interface.send("What is the type of post?", user="System", respond=False)
            elif msg_count == 2:
                self.chat_interface.send("What is the tone of voice?", user="System", respond=False)
            elif msg_count == 3:
                self.chat_interface.send("Please tell the agents what sort of information you are interested in knowing based on the file you uploaded!", user="System", respond=False)
            else:
                return

        async def callback(contents: str, user: str, instance: pn.chat.ChatInterface):
            global indicator

            # collect specifications from user input
            if self.rag_selected and file_input.value is not None:
                expected_msg_count = 4
            else:
                expected_msg_count = 3

            if (self.msg_count < expected_msg_count):
                base_questions(contents, self.msg_count)
                self.specifications[list(self.specifications.keys())[self.msg_count]] = contents
                self.msg_count += 1
                print(f"Message {self.msg_count} from {user}: {contents}")
                return
            
            self.specifications['tone_of_voice'] = contents

            if not self.initiate_chat_task_created:
                print("Creating task...")
                init_agents()
                self.chat_interface.send("Sending work to the agents, this migh take a while...", user="System", respond=False)
                # if file_input.value is None:
                if self.rag_selected and file_input.value is not None:
                    print("RAG Flow\n")
                    asyncio.create_task(delayed_initiate_chat(self.ragproxyagent, self.manager, contents))
                else:
                    print("No RAG Flow\n")
                    asyncio.create_task(delayed_initiate_chat(self.user_proxy, self.manager, contents))
            else:
                if self.input_future and not self.input_future.done():
                    self.input_future.set_result(contents)
                else:
                    self.chat_interface.send("The program has come to an unexpected halt, please try and refresh the page. If the problem persists, please contact the admin, thank you for your patience! ⭐️", user="System", respond=False)
                    print("No more messages awaited...")

        ### G U I  C O M P O N E N T S #####
        def add_openai_key_to_env(key): 
            SYSTEM_KWARGS = dict(
                user="System",
                respond=False,
            )
            if not key.startswith("sk-"):
                self.chat_interface.send("Please enter YOUR OWN ASSHOLE!!", **SYSTEM_KWARGS)
                return

            os.environ["OPENAI_API_KEY"] = key
            self.chat_interface.clear()
            self.chat_interface.send("Give a short description on the LinkedIn Post you wish to create 🙂", user="System", respond=False)
            self.chat_interface.disabled = False

        # MAIN COMPONENTS
        self.chat_interface = pn.chat.ChatInterface(callback=callback)
        self.chat_interface.disabled = True
        # Chat buttons
        self.chat_interface.show_rerun = False
        self.chat_interface.show_undo = False
        
        # COLUMN COMPONENTS
        api_key_input = None
        if os.environ.get("OPENAI_API_KEY") is None:
            self.chat_interface.send("Please enter you OpenAI key to begin the chat WITH YOUR ANUS!", user="System", respond=False)
            api_key_input = pn.widgets.PasswordInput(placeholder="sk-...", name="OpenAI Key")
            pn.bind(add_openai_key_to_env, key=api_key_input, watch=True)
        else:
            self.chat_interface.disabled = False
            # file_input.disabled = True
            self.chat_interface.send("Give a short description on the LinkedIn Post you wish to create 🙂", user="System", respond=False)


        return self.chat_interface


    
