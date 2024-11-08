import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import autogen
from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
from dotenv import load_dotenv
load_dotenv()

# Azure OpenAI for Dalle
api_version = os.getenv("AOAI_API_VERSION")
dalle3_model = os.getenv("DALL_E_MODEL_NAME")
api_base = os.getenv("AOAI_API_BASE")
# Initialize the DefaultAzureCredential
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

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
    ],
    "cache_seed": 42,
    "temperature": 0.5, 
    "max_tokens": 300
}

image_agent = MultimodalConversableAgent(
    name="image-explainer",
    max_consecutive_auto_reply=10,
    llm_config=llm_config,
)

user_proxy = autogen.UserProxyAgent(
    name="User_proxy",
    system_message="A human admin.",
    human_input_mode="NEVER",  # Try between ALWAYS or NEVER
    max_consecutive_auto_reply=0,
    code_execution_config={
        "use_docker": True
    },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)

# Ask the question with an image
user_proxy.initiate_chat(
    image_agent,
    message="""What's the breed of this dog?
<img https://th.bing.com/th/id/R.422068ce8af4e15b0634fe2540adea7a?rik=y4OcXBE%2fqutDOw&pid=ImgRaw&r=0>.""",
)

# Ask the question with an image
user_proxy.send(
    message="""What is this breed?
<img https://th.bing.com/th/id/OIP.29Mi2kJmcHHyQVGe_0NG7QHaEo?pid=ImgDet&rs=1>

Among the breeds, which one barks less?""",
    recipient=image_agent,
)