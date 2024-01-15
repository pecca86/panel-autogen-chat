import os
import json
from requests_oauthlib import OAuth1Session
import re
import asyncio
import autogen
import panel as pn

input_future = None


class Twitter:
    def __init__(self):
        self.initiate_chat_task_created = False
        self.posted = False
        self.input_future = None

    def get_twitter_chat(self):
        pn.extension()

        tweet_content = None

        class Tweeter:
            payload = None
            resource_owner_key = None
            resource_owner_secret = None

            def tweety(self, prompt, chat_interface, image=None) -> str:
                self.payload = {"text": prompt}
                print("Payload: ", self.payload["text"])

                cleaned_payload = re.sub(
                    '^"|"$', "", self.payload["text"]
                )  # cleans the double quotes from the tweet
                self.payload["text"] = cleaned_payload

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

                self.resource_owner_key = fetch_response.get("oauth_token")
                self.resource_owner_secret = fetch_response.get("oauth_token_secret")
                print("Got OAuth token: %s" % self.resource_owner_key)
                # Get authorization
                base_authorization_url = "https://api.twitter.com/oauth/authorize"
                authorization_url = oauth.authorization_url(base_authorization_url)

                print("Please go here and authorize: %s" % authorization_url)
                return "Please visit the link to authorize: %s. Enter the pin code in the field below." % authorization_url

            def get_shit_done(self, pin_code):    
                print("PIN ", pin_code)
                print("Token1 ", self.resource_owner_key)
                print("Token2 ", self.resource_owner_secret)
                print("PAYLOAD:", self.payload)
                verifier = pin_code

                # Get the access token
                access_token_url = "https://api.twitter.com/oauth/access_token"
                oauth = OAuth1Session(
                    "1FmnDkdwuvnuxmrP8ky1qgDv7",
                    client_secret="mXoZp1cnE9CcgdXbCcTii5NGAyUHur4qO7t8W0geYvrvjLbs88",
                    resource_owner_key=self.resource_owner_key,
                    resource_owner_secret=self.resource_owner_secret,
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
                    json=self.payload,
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


        twitter_client = Tweeter()

        config_list = [{
                'model': 'gpt-4-1106-preview',
                }]
        gpt4_config = {"config_list": config_list, "temperature":0, "seed": 53}

        def tweet(pin):
            chat_interface.send(f"Trying to post the tweet...", user="System", respond=False)
            chat_interface.disabled = True
            try:
                response = twitter_client.get_shit_done(pin)
            except BaseException as err:
                chat_interface.send(f"❌ It seems something went wrong, I got the message: {err} Unfortunately I am not able to recover from this error 🙈",  user="System", respond=False) #TODO: Create mechanism for retrying / restarting fresh session
            chat_interface.send(f"✅ Successfully tweeted the post with the following response: {response}",  user="System", respond=False)

        def add_key_to_env(key):
            tweet(key)

        async def post_pin():
            global tweet_content
            response = twitter_client.tweety(tweet_content, chat_interface)
            chat_interface.send(response, user=user_proxy.name, respond=False)
            # chat_interface.disabled = False
            if self.input_future is not None:
                self.input_future.cancel()
            key_input = pn.widgets.PasswordInput(placeholder="Seven digits long number", name="Authorization code")
            pn.bind(add_key_to_env, key=key_input, watch=True)
            chat_interface.append(key_input)


        import sys
        async def handle_click(event):
            print("Posting tweet!")
            event.disabled = True
            chat_interface.send("Posting tweet!", user=user_proxy.name, respond=False)
            await post_pin()

        class MyConversableAgent(autogen.ConversableAgent):

            def set_posted(self, posted):
                self.posted = posted

            def set_input_future(self, input_future):
                self.input_future = input_future

            async def a_get_human_input(self, prompt: str) -> str:
                chat_interface.send(prompt, user="System", respond=False)
                button = pn.widgets.Button(name='Post the tweet!', button_type='primary')
                pn.bind(handle_click, button, watch=True)
                chat_interface.append(button)
                # Create a new Future object for this input operation if none exists
                if self.posted:
                    return
                if self.input_future is None or self.input_future.done():
                    self.input_future = asyncio.Future()

                # Wait for the callback to set a result on the future
                await self.input_future

                # Once the result is set, extract the value and reset the future for the next input operation
                input_value = self.input_future.result()
                self.input_future = None
                return input_value

        user_proxy = MyConversableAgent(
        name="Admin",
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
        system_message="""A human admin. Interact with the twitter_agent to discuss the tweet. Prompt needs to be approved by this admin. 
        
        """,
        code_execution_config=False,
        human_input_mode="ALWAYS",
        )
        user_proxy.set_posted(self.posted)
        user_proxy.set_input_future(self.input_future)

        twitter_agent_name = "twitter_agent"
        twitter_agent = autogen.AssistantAgent(
            name=twitter_agent_name,
            system_message="create a tweet based on the user_proxy's message. You will iterate with the critic_agent to improve the tweet based on the critic_agents feedback. You will stop and wait for Admin feedback once you get a score of 4/5 or above.",
            llm_config={
                "config_list": config_list,
                "temperature": 0.5,
                "frequency_penalty": 0.1,
            }
        )
        criteria_list = ["grammar", "clarity", "conciseness", "originality", "humor", "emotion", "relevance", "overall"]
        critic_agent = autogen.AssistantAgent(
            name="critic_agent",
            system_message=f"You are the critic_agent. You will provide feedback to the twitter_agent on how to improve the tweet. You will provide feedback on the following critera {criteria_list}. You will ALWAYS check that the tweet contains a MAXIMUM of 240 words, this is IMPORTANT! The tweet is good when the score is a minumum of 4/5. Also take into account the Admin's feedback!",
            llm_config={
                "config_list": config_list,
                "temperature": 0,
                "frequency_penalty": 0,
            }
        )


        ###############

        groupchat = autogen.GroupChat(agents=[user_proxy, twitter_agent, critic_agent], messages=[], max_round=20)
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

        avatar = {user_proxy.name:"👨‍💼", twitter_agent.name:"👩‍💻", critic_agent.name:"👨‍🏫"}


        def print_messages(recipient, messages, sender, config):

            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

            if all(key in messages[-1] for key in ['name']):
                chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
                if messages[-1]['name'] == twitter_agent_name:
                    global tweet_content
                    tweet_content = messages[-1]['content']
                    
            else:
                return False, None  # required to ensure the agent communication flow continues
            
            return False, None  # required to ensure the agent communication flow continues

        user_proxy.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        )

        twitter_agent.register_reply(
            [autogen.Agent, None],
            reply_func=print_messages, 
            config={"callback": None},
        ) 

        critic_agent.register_reply(
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
                asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

            else:
                if self.input_future and not self.input_future.done():
                    self.input_future.set_result(contents)
                else:
                    chat_interface.send("Please refresh the browser to create a new chat session!", user="System", respond=False)
                    chat_interface.disabled = True

        chat_interface = pn.chat.ChatInterface(callback=callback)
        chat_interface.send("Type an idea for a tweet!", user="System", respond=False)
        return chat_interface
            

