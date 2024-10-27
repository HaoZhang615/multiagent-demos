import os
import streamlit as st
import asyncio
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen import ConversableAgent, register_function
from typing import Annotated, Literal
import requests
from openai import AzureOpenAI
from datetime import datetime
import json
from dotenv import load_dotenv
load_dotenv()


# This example pulls from this tutorial https://microsoft.github.io/autogen/docs/tutorial/tool-use/ and we added Streamlit to it. 
# You could remove the UI aspect and just run it as a script.
# To run this script you will need to make sure you have the packages installed (autogen, azure-identity, streamlit, asyncio) and you will need to have an Azure account with a Cognitive Services resource.
# To run the app, you will use the command in your terminal: streamlit run toolsapp.py
# You will need to replace the model, base_url, and api_version with your own values.
# When the app is running it will open in a browser window and will take a few seconds to load. Once it is loaded you can type in the chat box and the AI will respond.
# To test the tool that is shown here ( calculator ) you can type in the chat box something like "What is (44232 + 13312 / (232 - 32)) * 5?" and the AI will respond with the answer."
# This helps illustrate how to use and register a tool with the AutoGen agents. 

Operator = Literal["+", "-", "*", "/"]

# Set the title of the app
st.title("2 agents with multiple tools")
# Initialize the DefaultAzureCredential
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)
# Bing Search API
bing_search_api_key = os.getenv("BING_SEARCH_API_KEY")
bing_search_api_endpoint = os.getenv("BING_SEARCH_API_ENDPOINT")
# Azure OpenAI for Dalle
api_version = os.getenv("AOAI_API_VERSION")
dalle3_model = os.getenv("DALL_E_MODEL_NAME")
api_base = os.getenv("AOAI_API_BASE")

llm_config = {
    "config_list": [
        {
            "model":  os.getenv("GPT_4o_mini_Model_Name"),
            "base_url": api_base,
            "api_type": "azure",
            "api_version": api_version,
            "max_tokens": 1000,
            "azure_ad_token_provider": token_provider
        }
    ]
}

## Simple Tool or Skill for this example. 
## A simple calculator that can perform addition, subtraction, multiplication, and division.
## Please reference this tutorial for more information https://microsoft.github.io/autogen/docs/tutorial/tool-use/ as this example pulls that directly

def calculator(a: int, b: int, operator: Annotated[Operator, "operator"]) -> int:
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    elif operator == "*":
        return a * b
    elif operator == "/":
        return int(a / b)
    else:
        raise ValueError("Invalid operator")
    
def web_searcher(query: str, up_to_date:bool=False) -> str:

    headers = {"Ocp-Apim-Subscription-Key": bing_search_api_key}
    question = query
    params = {"q": question, "count": 3}  # Limit the results to 5
    if up_to_date:
            params.update({"sortby":"Date"})
    try:
        response = requests.get(bing_search_api_endpoint, headers=headers,params = params)
        print(params)
        response.raise_for_status()
        search_results = response.json()
        results = []
        if search_results is not None:
            for v in search_results["webPages"]["value"]:
                result = {
                    "title": v["name"],
                    "content": v["snippet"],
                    "source_url": v["url"]
                }
                results.append(result)
            return [
                    {"content": doc["content"],
                    "source_page": doc["title"],
                    "source_url":doc["source_url"]}
                for doc in results]
        return json.dumps(results)
    except Exception as ex:
        raise ex
def image_generator(prompt: str) -> str:
    token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
    client = AzureOpenAI(
            api_version="2024-02-01",  
            azure_ad_token_provider=token_provider, 
            azure_endpoint=api_base
        )
    result = client.images.generate(
            model=dalle3_model, # the name of your DALL-E 3 deployment
            prompt=prompt,
            n=1
        )
    json_response = json.loads(result.model_dump_json())
    # Retrieve the generated image
    image_url = json_response["data"][0]["url"]  # extract image URL from response
    print(f"Image URL: {image_url}")
    return image_url
    # define function to get today's date as string format MMMM DD, YYYY
def get_today_date() -> str:
    return datetime.today().strftime("%B %d, %Y")
## We need to extend the ConversableAgent class to track the conversation in Streamlit
class TrackableAssistantAgent(ConversableAgent):

    def __init__(self, *args, skills=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.skills = skills or []
        
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)
    

## We need to extend the ConversableAgent class to track the conversation in Streamlit
class TrackableUserProxyAgent(ConversableAgent):
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)


# Let's first define the assistant agent that suggests tool calls. You can modify for your own tools. 
assistant = TrackableAssistantAgent(
    name="Assistant",
    system_message="""You are a helpful AI assistant that help people with complext tasks.
    You have access to 4 tools: calculator, web_searcher, image_generator and get_today_date.
    You can help with multistep tasks by making an execution plan and sequentially using the tools. 
    Reason step by step which actions to take to get to the answer.
    When you give the final answer, provide the key reasoning steps you took to get to the answer.
    Return 'TERMINATE' when the task is done.""",
    llm_config=llm_config,
)

# The user proxy agent is used for interacting with the assistant agent
# and executes tool calls.
user_proxy = TrackableUserProxyAgent(
    name="User",
    system_message="""You act on behalf of the user to monitor the assistant's actions for solving the task given by the user. 
    You examine if the assistant is making the right plan and suggesting the right tool to use. If it is the case, execute the tool.
    Before outputing the final result, validate the web search result and make sure any image url is represented as markdown image that is visible in the chat application.
    """,
    llm_config=llm_config,
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    human_input_mode="TERMINATE",
)

# Registering the functions
# Register the calculator function as a tool. If you modify this you need to change the name, and the description. 
register_function(
    calculator,
    caller=assistant,  # The assistant agent can suggest calls to the calculator.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="calculator",  # By default, the function name is used as the tool name.
    description="A simple calculator",  # A description of the tool.
)
# Register the image_generator function as a tool. If you modify this you need to change the name, and the description. 
register_function(
    image_generator,
    caller=assistant,  # The assistant agent can suggest calls to the calculator.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="image_generator",  # By default, the function name is used as the tool name.
    description="A image generator that calls Dall-E API to generate an image based on the input prompt",  # A description of the tool.
)
# Register the web_searcher function as a tool. If you modify this you need to change the name, and the description. 
register_function(
    web_searcher,
    caller=assistant,  # The assistant agent can suggest calls to the calculator.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="web_searcher",  # By default, the function name is used as the tool name.
    description="A web searcher that calls Bing Search API to search the web and return a list of search result based on a query. If the query requires up-to-date information, overright the <up_to_date> parameter to 'true'",  # A description of the tool.
)
# Register the get_today_date function as a tool. If you modify this you need to change the name, and the description. 
register_function(
    get_today_date,
    caller=assistant,  # The assistant agent can suggest calls to the calculator.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="get_today_date",  # By default, the function name is used as the tool name.
    description="A simple function to get today's date",  # A description of the tool.
)


if 'chat_initiated' not in st.session_state:
    st.session_state.chat_initiated = False

chatresult = None
with st.container():
 
    user_input = st.chat_input("Type something...")
    if user_input:
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def initiate_chat():
            
            try:
                chatresult = user_proxy.initiate_chat(
                    assistant,
                    message=user_input,
                    max_consecutive_auto_reply=5,
                    is_termination_msg=lambda x: x.get("content", "").strip().endswith("TERMINATE"),
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")
        
        loop.run_until_complete(initiate_chat())
        loop.close()

if st.session_state.chat_initiated:
    st.write(chatresult)
        
