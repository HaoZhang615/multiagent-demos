import os
import streamlit as st
import asyncio
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen import GroupChat, GroupChatManager, ConversableAgent, register_function
from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
from autogen.agentchat.contrib.capabilities.vision_capability import VisionCapability
from typing import Annotated, Literal
import requests
from openai import AzureOpenAI
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Streamlit UI setup
st.write("# AutoGen Demos")
st.write("## AutoGen Group Chat")

# Initialize Azure credentials
def initialize_token_provider():
    return get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )

token_provider = initialize_token_provider()

# Load environment variables for APIs
def load_api_keys():
    return {
        "bing_search_api_key": os.getenv("BING_SEARCH_API_KEY"),
        "bing_search_api_endpoint": os.getenv("BING_SEARCH_API_ENDPOINT"),
        "api_version": os.getenv("AOAI_API_VERSION"),
        "dalle3_model": os.getenv("DALL_E_MODEL_NAME"),
        "api_base": os.getenv("AOAI_API_BASE"),
        "gpt_model_name": os.getenv("GPT_4o_mini_Model_Name")
    }

api_keys = load_api_keys()

# LLM configuration
llm_config = {
    "cache_seed": 41,
    "temperature": 0,
    "timeout": 120,
    "config_list": [
        {
            "model": api_keys["gpt_model_name"],
            "base_url": api_keys["api_base"],
            "api_type": "azure",
            "api_version": api_keys["api_version"],
            "max_tokens": 1000,
            "azure_ad_token_provider": token_provider
        }
    ]
}

# Define tools
def web_search(query: str, up_to_date: bool = False) -> str:
    headers = {"Ocp-Apim-Subscription-Key": api_keys["bing_search_api_key"]}
    params = {"q": query, "count": 7}
    if up_to_date:
        params.update({"sortby": "Date"})
    try:
        response = requests.get(api_keys["bing_search_api_endpoint"], headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()
        results = [
            {
                "title": v["name"],
                "content": v["snippet"],
                "source_url": v["url"]
            }
            for v in search_results.get("webPages", {}).get("value", [])
        ]
        return json.dumps(results)
    except Exception as ex:
        st.error(f"Error during web search: {ex}")
        return ""

def image_generation(prompt: str) -> str:
    client = AzureOpenAI(
        api_version="2024-02-01",
        azure_ad_token_provider=token_provider,
        azure_endpoint=api_keys["api_base"]
    )
    try:
        result = client.images.generate(
            model=api_keys["dalle3_model"],
            prompt=prompt,
            n=1
        )
        json_response = json.loads(result.model_dump_json())
        image_url = json_response["data"][0]["url"]
        return image_url
    except Exception as ex:
        st.error(f"Error during image generation: {ex}")
        return ""

def get_today_date() -> str:
    return datetime.today().strftime("%B %d, %Y")

# Define agents
class TrackableAssistantAgent(ConversableAgent):
    def __init__(self, *args, skills=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.skills = skills or []

    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)

class TrackableUserProxyAgent(ConversableAgent):
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)
    
class TrackableMultimodalAgent(MultimodalConversableAgent):
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)

# Initialize agents
user_proxy = TrackableUserProxyAgent(
    name="Admin",
    system_message="""A human admin. Interact with the planner to discuss the plan. 
    Plan execution needs to be approved by this admin. Admin can execute code and tool useage.""",
    code_execution_config={
            "last_n_messages": 2,
            "work_dir": "output",
            "use_docker": True,
        },
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
    human_input_mode="NEVER",
)
image_explainer = TrackableMultimodalAgent(
    name="image-explainer",
    max_consecutive_auto_reply=10,
    llm_config=llm_config,
    system_message="Your explain the image you see with a engaging description.",
)

planner = TrackableAssistantAgent(
    name="Planner",
    system_message="Planner. Suggest a plan. Revise the plan based on feedback from User_proxy and critic, until admin approval.",
    llm_config=llm_config,
)

critic = ConversableAgent(
    name="Critic",
    system_message="Critic. Double check plan, claims, code from other agents and provide feedback.",
    llm_config=llm_config,
)

date_checker = TrackableAssistantAgent(
    name="Date Checker",
    llm_config=llm_config,
    system_message="Date Checker. You can use the get_today_date tool to get today's date.",
)

# Register functions
register_function(
    get_today_date,
    caller=date_checker,
    executor=user_proxy,
    name="get_today_date",
    description="A simple function to get today's date",
)

# Initialize group chat
group_chat = GroupChat(
    agents=[user_proxy, image_explainer, planner, critic, date_checker],
    messages=[],
    max_round=10,
)
vision_capability = VisionCapability(lmm_config=llm_config)
manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
vision_capability.add_to_agent(manager)

# Streamlit session state
if 'chat_initiated' not in st.session_state:
    st.session_state.chat_initiated = False

# Chat interaction
def initiate_chat(user_input):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def chat():
        try:
            return await user_proxy.initiate_chat(
                manager,
                message=user_input,
                max_consecutive_auto_reply=20,
                is_termination_msg=lambda x: x.get("content", "").strip().endswith("TERMINATE"),
            )
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return None
    st.session_state.chat_initiated = True

    chat_result = loop.run_until_complete(chat())
    loop.close()
    return chat_result

with st.container():
    user_input = st.chat_input("Type something...")
    if user_input:
        chat_result = initiate_chat(user_input)
        if chat_result:
            st.write(chat_result)
