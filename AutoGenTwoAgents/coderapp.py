import asyncio
import streamlit as st
from autogen import AssistantAgent, UserProxyAgent, register_function
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from datetime import datetime

# Initialize the DefaultAzureCredential
# This will be used to authenticate rather than use a key directly
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

# Our configuration for the LLM model. 
# You will need to provide the model, the base url which you can find from your Azure resource, the api type, the api version, the max tokens, and the token provider. 
llm_config = {
    "config_list": [
        {
            "model":  "gpt-4o-mini",
            "base_url": "https://hz-aoai.openai.azure.com/",
            "api_type": "azure",
            "api_version": "2024-02-01",
            "max_tokens": 1000,
            "azure_ad_token_provider": token_provider
        }
    ]
}

# define function to get today's date as string format MMMM DD, YYYY
def get_today_date() -> str:
    return datetime.today().strftime("%B %d, %Y")

# We will create a class that extends the AssistantAgent class to track the messages sent by the assistant 
# so we can tap it into the Streamlit chat messages.
class TrackableAssistantAgent(AssistantAgent):        
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)
    

# We will create a class that extends the AssistantAgent class to track the messages sent by the assistant 
# so we can tap it into the Streamlit chat messages.
class TrackableUserProxyAgent(UserProxyAgent):
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)


# Set the title of the app
st.title("Code Interpreter")

# Create a user proxy agent that will be used to interact with the user
# Note that this agent can execute code. work_dir is the directory where the code will be executed.
user_proxy = TrackableUserProxyAgent(
        name="User_proxy",
        system_message="A helful AI Assistant.",
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": "coder_output",
            "use_docker": True,
        },  # Please set use_docker=True if docker is available to run the generated code. 
            # Using docker is safer than running the generated code directly.
        human_input_mode="TERMINATE",
        )

# Create a coder agent that will be used to solve the tasks  
assistant = TrackableAssistantAgent(
            name="Assistant",
            llm_config=llm_config,
            system_message="""You are a helpful AI assistant.
            You have access to a tool: get_today_date.
            Solve tasks using your coding and language skills.
            In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
            1. When you need to collect info, use the code to output the info you need, 
            for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
            2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
            Solve the task step by step if you need to. 
            If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
            When using code, you must indicate the script type in the code block. 
            The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. 
            The user can't modify your code. So do not suggest incomplete code which requires users to modify. 
            Don't use a code block if it's not intended to be executed by the user.
            If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. 
            Don't include multiple code blocks in one response. 
            Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. 
            Check the execution result returned by the user.If the result indicates there is an error, fix the error and output the code again. 
            Suggest the full code instead of partial code or code changes. 
            If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
            When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
            Reply \"TERMINATE\" in the end when everything is done.""",
        )

# Register the get_today_date function as a tool. If you modify this you need to change the name, and the description. 
register_function(
    get_today_date,
    caller=assistant,  # The assistant agent can suggest calls to the get_today_date.
    executor=user_proxy,  # The user proxy agent can execute the calculator calls.
    name="get_today_date",  # By default, the function name is used as the tool name.
    description="A simple function to get today's date",  # A description of the tool.
)       

if 'chat_initiated' not in st.session_state:
    st.session_state.chat_initiated = False

chatresult = None

# Creating a Streamlit container to hold the chat messages and the input 
with st.container():

    # Create a chat input for the user to type in
    user_input = st.chat_input("Type something...")
    # If the user input is not empty, we will initiate the chat
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
        
