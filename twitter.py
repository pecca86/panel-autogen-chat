import os
import json
import sys
from requests_oauthlib import OAuth1Session
import re
import asyncio
import autogen
import panel as pn

pn.extension(notifications=True)

input_future = None

class TwitterChat:

    chat_interface = None

    loading_spinner = pn.indicators.LoadingSpinner(value=False, width=50, height=50, name="Loading...")

    def __init__(self):
        self.initiate_chat_task_created = False
        self.posted = False
        self.input_future = None

    def is_loading(self):
        self.loading_spinner.value = True

    def is_waiting_input(self):
        self.loading_spinner.value = False

    def get_twitter_chat(self):
        pn.extension()
        self.tweet_content = None

        class Tweeter:
            payload = None
            resource_owner_key = None
            resource_owner_secret = None
            
            def __init__(self, chat) -> None:
                self.chat_interface = chat

            def tweety(self, prompt, image=None) -> str:
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
                    self.chat_interface.send("There may have been an issue with the consumer_key or consumer_secret you entered.", user="System", respond=False)

                self.resource_owner_key = fetch_response.get("oauth_token")
                self.resource_owner_secret = fetch_response.get("oauth_token_secret")
                print("Got OAuth token: %s" % self.resource_owner_key)
                # Get authorization
                base_authorization_url = "https://api.twitter.com/oauth/authorize"
                authorization_url = oauth.authorization_url(base_authorization_url)

                print("Please go here and authorize: %s" % authorization_url)
                return "Please visit the link to authorize: %s. Enter the pin code in the field below." % authorization_url

            def post_tweet(self, pin_code):    
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

                # Saving the response as JSON
                json_response = response.json()

                return json_response

        twitter_client = Tweeter(self.chat_interface)

        config_list = [{
                'model': 'gpt-4-1106-preview',
                }]
        gpt4_config = {"config_list": config_list, "temperature":0, "seed": 53}

        def tweet(pin):
            self.chat_interface.send(f"Trying to post the tweet...", user="System", respond=False)
            self.chat_interface.disabled = True
            try:
                response = twitter_client.post_tweet(pin)

                print("Response from Twitter: ", response)

                self.chat_interface.send(f"✅ Successfully tweeted the post with the following response: {response}",  user="System", respond=False)
            except BaseException as err:
                self.chat_interface.send(f"❌ It seems something went wrong, I got the message: {err}. Unfortunately I am not able to recover from this error 🙈",  user="System", respond=False) #TODO: Create mechanism for retrying / restarting fresh session

        def add_token(key):
            tweet(key)

        async def post_pin():
            response = twitter_client.tweety(user_proxy.get_final_tweet())
            self.chat_interface.send(response, user="System", respond=False)
            if self.input_future is not None:
                self.input_future.cancel()
            key_input = pn.widgets.PasswordInput(placeholder="Seven digits long number", name="Authorization code")
            pn.bind(add_token, key=key_input, watch=True)
            self.chat_interface.append(key_input)

        async def handle_post(event):
            print("Posting tweet!")
            self.chat_interface.send("Posting tweet!", user="System", respond=False)
            await post_pin()

        class MyConversableAgent(autogen.ConversableAgent):

            final_tweet = None
            chat_interface = None

            def set_posted(self, posted):
                self.posted = posted

            def set_input_future(self, input_future):
                self.input_future = input_future
            
            def set_tweet_content(self, tweet_content):
                self.tweet_content = tweet_content

            def set_final_tweet(self, final_tweet):
                self.final_tweet = final_tweet
            
            def get_final_tweet(self):
                if self.final_tweet is None:
                    return self.tweet_content
                return self.tweet_content
            
            def set_chat_interface(self, chat_interface):
                self.chat_interface = chat_interface

            async def a_get_human_input(self, prompt: str) -> str:
                def edit_tweet(event):
                    self.set_final_tweet(tweet_text.value)
                    pn.state.notifications.position = "top-center"
                    pn.state.notifications.success("Tweet updated!", duration=2000)

                self.chat_interface.send(prompt, user="System", respond=False)
                tweet_text = pn.widgets.TextAreaInput(
                    auto_grow=True, 
                    max_rows=30,
                    rows=5, 
                    value=self.tweet_content, 
                    name="Image Prompt",
                    width=1100,
                    height=150
                )
                pn.bind(edit_tweet, tweet_text, watch=True)
                post_button = pn.widgets.Button(name='Post the tweet!', button_type='primary')
                pn.bind(handle_post, post_button, watch=True)
                self.chat_interface.loading = False
                self.chat_interface.send(tweet_text, user="System", respond=False)
                self.chat_interface.append(post_button)
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
            system_message="create a tweet based on the user_proxy's message. The tweet should NOT have more than 240 words in it, this is IMPORTANT!. You will iterate with the critic_agent to improve the tweet based on the critic_agents feedback. You will stop and wait for Admin feedback once you get a score of 4/5 or above.",
            llm_config={
                "config_list": config_list,
                "temperature": 0.5,
                "frequency_penalty": 0.1,
            }
        )
        criteria_list = ["grammar", "clarity", "conciseness", "originality", "humor", "emotion", "relevance", "overall", "word count"]
        critic_agent = autogen.AssistantAgent(
            name="critic_agent",
            system_message=f"You are the critic_agent. You will provide feedback to the twitter_agent on how to improve the tweet. You will provide feedback on the following critera {criteria_list}. You will ALWAYS check that the tweet contains a MAXIMUM of 240 words, this is IMPORTANT! The tweet is good when the score is a minumum of 4/5. Also take into account the Admin's feedback!",
            llm_config={
                "config_list": config_list,
                "temperature": 0,
                "frequency_penalty": 0,
            }
        )

        groupchat = autogen.GroupChat(agents=[user_proxy, twitter_agent, critic_agent], messages=[], max_round=20)
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

        avatar = {user_proxy.name:"👨‍💼", twitter_agent.name:"👩‍💻", critic_agent.name:"👨‍🏫"}

        def print_messages(recipient, messages, sender, config):

            print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

            if all(key in messages[-1] for key in ['name']):
                # Don't echo the User message as Admin in the chat interface
                if messages[-1]['name'] == user_proxy.name:
                    return False, None  # required to ensure the agent communication flow continues
                
                self.chat_interface.send(messages[-1]['content'], user=messages[-1]['name'], avatar=avatar[messages[-1]['name']], respond=False)
                if messages[-1]['name'] == twitter_agent_name:
                    self.tweet_content = messages[-1]['content']
                    user_proxy.set_tweet_content(self.tweet_content)
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
            print("USER: ", user)
            self.chat_interface.loading = True
            if not self.initiate_chat_task_created:
                asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

            else:
                if self.input_future and not self.input_future.done():                   
                    self.input_future.set_result(contents)
                else:
                    self.chat_interface.send("Please refresh the browser to create a new chat session!", user="System", respond=False)
                    self.chat_interface.disabled = True



        def print_about(instance, event):
            instance.send("""This is the twitter flow.
                             The following bugs are known:
                                - Sometimes the chat manager can pass the user's first input to the critic agent instead of the twitter agent.
                                - Sometimes the chat inteface does not scroll all the way down, so you need to scroll manually.
                          """, 
                          respond=False, 
                          user="System"
                        )

        self.chat_interface = pn.chat.ChatInterface(
            callback=callback, 
            button_properties={
                "about": {"callback": print_about, "icon": "help"},
            }
        )
        self.chat_interface.show_rerun = False
        self.chat_interface.show_undo = False

        user_proxy.set_chat_interface(self.chat_interface)
        return self.chat_interface
            

