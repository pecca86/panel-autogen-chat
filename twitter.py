import os
import json
from requests_oauthlib import OAuth1Session
import re
import asyncio
import autogen
import panel as pn

input_future = None


class Twitter:
    def __self__(self):
        pass


    # "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"

    def get_twitter_chat(self):
        os.environ["OPENAI_API_KEY"] = ""

        config_list = [
            {
                'model': 'gpt-4-1106-preview',
            }
            ]
        gpt4_config = {"config_list": config_list, "temperature":0, "seed": 53}


        class MyConversableAgent(autogen.ConversableAgent):

            async def a_get_human_input(self, prompt: str) -> str:
                global input_future
                chat_interface.send(prompt, user="System", respond=False)
                # Create a new Future object for this input operation if none exists
                if input_future is None or input_future.done():
                    input_future = asyncio.Future()

                # Wait for the callback to set a result on the future
                await input_future

                # Once the result is set, extract the value and reset the future for the next input operation
                input_value = input_future.result()
                input_future = None
                return input_value

        user_proxy = MyConversableAgent(
        name="Admin",
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
        system_message="""A human admin. Interact with the image_agent to discuss the tweet. Prompt needs to be approved by this admin. 
        
        """,
        code_execution_config=False,
        human_input_mode="ALWAYS",
        )
        ###############
        def post_tweet(prompt):
            twitter = Tweeter()
            response = twitter.tweety(prompt, chat_interface)
            print(response)
            return response

        image_agent_name = "image_agent"
        image_agent = autogen.AssistantAgent(
            name=image_agent_name,
            system_message="create a tweet based on the user_proxy's message",
            llm_config={
                "config_list": config_list,
                "temperature": 0.5,
                "frequency_penalty": 0.1,
            }
        )

        function_agent = autogen.AssistantAgent(
            name="function_agent",
            system_message="You are a helpful assistant. Reply TERMINATE when the task is done.",
            llm_config={
                "timeout": 600,
                "seed": 42,
                "config_list": config_list,
                "model": "gpt-4",  # make sure the endpoint you use supports the model
                "temperature": 0,
                "frequency_penalty": 0,
                "functions": [
                    {
                        "name": "post_tweet",
                        "description": "always use the post_tweet function",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "prompt: the prompt to use for generating the tweet",
                                },
                            },
                            "required": ["prompt"],
                        },
                    }
                ],
            },
        )

        coder_agent_name = "coder_agent"
        coder_agent = autogen.AssistantAgent(
            name = coder_agent_name,
            system_message=f"You are the {coder_agent_name}. Your task is to print to the chat the reponse from the post_tweet function.",
            llm_config={
                "config_list": config_list,
                "temperature": 0,
                "frequency_penalty": 0,
            }
        )

        user_proxy_executor = autogen.UserProxyAgent(
            system_message="You are responsible for calling the function post_tweet which will return the response from the twitter API. You will print this response to the chat.",
            human_input_mode="TERMINATE",
            is_termination_msg=lambda x: x.get("content", "")
            and x.get("content", "").rstrip().endswith("TERMINATE"),
            max_consecutive_auto_reply=20,
            name="user_proxy",
            code_execution_config={"work_dir": "dall_e_img", "use_docker": False},
            function_map={"post_tweet": post_tweet},
        )



        ###############

        # executor = autogen.UserProxyAgent(
        #     name="Executor",
        #     system_message="Executor. Execute the code written by the function_agent and report the result.",
        #     human_input_mode="NEVER",
        #     code_execution_config={"last_n_messages": 3, "work_dir": "paper"},
        # )

        groupchat = autogen.GroupChat(agents=[user_proxy, image_agent, function_agent, coder_agent, user_proxy_executor], messages=[], max_round=20)
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

        avatar = {user_proxy.name:"👨‍💼", image_agent.name:"👩‍💻", function_agent.name:"👩‍🔬", coder_agent.name:"🗓", user_proxy_executor.name:"Olle", "post_tweet": "post_tweet"}

        def print_messages(recipient, messages, sender, config):

            #chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")
            
            if all(key in messages[-1] for key in ['name']):
                chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
            else:
                # chat_interface.send(messages[-1]['content'], user='SecretGuy', avatar='🥷', respond=False)
                return False, None  # required to ensure the agent communication flow continues
            
            return False, None  # required to ensure the agent communication flow continues

        user_proxy.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        )
        user_proxy_executor.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages,
            config={"callback": None},
        )
        image_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        ) 
        function_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        ) 
        coder_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        )

        pn.extension(design="material")

        self.initiate_chat_task_created = False

        async def delayed_initiate_chat(agent, recipient, message):

            self.initiate_chat_task_created
            # Indicate that the task has been created
            self.initiate_chat_task_created = True

            # Wait for 2 seconds
            await asyncio.sleep(2)

            # Now initiate the chat
            await agent.a_initiate_chat(recipient, message=message)

        async def callback(contents: str, user: str, instance: pn.chat.ChatInterface):
            
            self.initiate_chat_task_created
            global input_future

            if not self.initiate_chat_task_created:
                asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

            else:
                if input_future and not input_future.done():
                    input_future.set_result(contents)
                else:
                    print("There is currently no input being awaited.")

        chat_interface = pn.chat.ChatInterface(callback=callback)


        ###############
        # TWITTER API #
        ###############
        class Tweeter:
            
            def tweety(self, prompt, chat_interface, image=None) -> json:

                payload = {"text": prompt}
                print("Payload: ", payload["text"])

                cleaned_payload = re.sub(
                    '^"|"$', "", payload["text"]
                )  # cleans the double quotes from the tweet
                payload["text"] = cleaned_payload

                # Get request token
                request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
                oauth = OAuth1Session(
                    "1FmnDkdwuvnuxmrP8ky1qgDv7",
                    client_secret="mXoZp1cnE9CcgdXbCcTii5NGAyUHur4qO7t8W0geYvrvjLbs88",
                )

                try:
                    fetch_response = oauth.fetch_request_token(request_token_url)
                except ValueError:
                    print("There may have been an issue with the consumer_key or consumer_secret you entered.")
                    chat_interface.send("There may have been an issue with the consumer_key or consumer_secret you entered.", user="System", respond=False)

                resource_owner_key = fetch_response.get("oauth_token")
                resource_owner_secret = fetch_response.get("oauth_token_secret")
                print("Got OAuth token: %s" % resource_owner_key)
                auth_token_response = "Got OAuth token: %s" % resource_owner_key
                chat_interface.send(auth_token_response, user="System", respond=False)
                # Get authorization
                base_authorization_url = "https://api.twitter.com/oauth/authorize"
                authorization_url = oauth.authorization_url(base_authorization_url)

                print("Please go here and authorize: %s" % authorization_url)
                auth_url_response = "Please go here and authorize: %s" % authorization_url
                chat_interface.send(auth_url_response, user="System", respond=True) # check if true / false
                chat_interface.send("Please enter the PIN in the running console.", user="System", respond=False)
                verifier = input("Paste the PIN here: ")

                # Get the access token
                access_token_url = "https://api.twitter.com/oauth/access_token"
                oauth = OAuth1Session(
                    "1FmnDkdwuvnuxmrP8ky1qgDv7",
                    client_secret="mXoZp1cnE9CcgdXbCcTii5NGAyUHur4qO7t8W0geYvrvjLbs88",
                    resource_owner_key=resource_owner_key,
                    resource_owner_secret=resource_owner_secret,
                    verifier=verifier,
                )
                oauth_tokens = oauth.fetch_access_token(access_token_url)

                access_token = oauth_tokens["oauth_token"]
                access_token_secret = oauth_tokens["oauth_token_secret"]

                # Make the request
                oauth = OAuth1Session(
                    "1FmnDkdwuvnuxmrP8ky1qgDv7",
                    client_secret="mXoZp1cnE9CcgdXbCcTii5NGAyUHur4qO7t8W0geYvrvjLbs88",
                    resource_owner_key=access_token,
                    resource_owner_secret=access_token_secret,
                )

                # Making the request
                response = oauth.post(
                    "https://api.twitter.com/2/tweets",
                    json=payload,
                )

                if response.status_code != 201:
                    raise Exception(
                        "Request returned an error: {} {}".format(
                            response.status_code, response.text
                        )
                    )

                print("Response code: {}".format(response.status_code))
                response_code = "Response code: {}".format(response.status_code)
                chat_interface.send(response_code, user="System", respond=False)

                # Saving the response as JSON
                json_response = response.json()

                return json_response
        return chat_interface
            

