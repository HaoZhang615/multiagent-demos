import tempfile
import asyncio
import streamlit as st
from autogen import ConversableAgent, AssistantAgent, UserProxyAgent, register_function
from autogen.coding import DockerCommandLineCodeExecutor
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from datetime import datetime
from io import StringIO
import os

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
            "max_tokens": 2000,
            "azure_ad_token_provider": token_provider
        }
    ],
    "temperature": 0, 
}

# # Create a temporary directory to store the code files.
# temp_dir = tempfile.TemporaryDirectory()

# Create a Docker command line code executor.
executor = DockerCommandLineCodeExecutor(
    image="python:3.12-slim",  # Execute code using the given docker image name.
    timeout=10,  # Timeout for each code execution in seconds.
    work_dir="work_dir",  # Use the temporary directory to store the code files.
)

# define function to get today's date as string format MMMM DD, YYYY
def get_today_date() -> str:
    return datetime.today().strftime("%B %d, %Y")

# We will create a class that extends the ConversableAgent class to track the messages sent by the agent 
# so we can tap it into the Streamlit chat messages.
class TrackableConversableAgent(ConversableAgent):        
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)

# Set the title of the app
st.title("2 Agents Chat App with coding capability")

# add a description on how to use the app
st.markdown(f"""#### This app allows you to give a task to an AI assistant. A user proxy agent will do code execution and give feedback to the AI assistant on your behalf.""")
st.markdown(f"""#### You can chat with the AI assistant and the user proxy agent by typing in the chat box below.""")
st.markdown(f"""##### Optionally, you can upload a file from local (by clicking on the file upload element below) to reference in your task assignment.""")
st.markdown(f"""##### The user proxy agent will use the uploaded file to ground the task solving process. Delete the file from the work directory by clicking on the *Clear work directory* button below.""")

# Create a function to clear the work directory
def clear_work_dir():
    for file in os.listdir("work_dir"):
        os.remove(os.path.join("work_dir", file))
    return st.success("Work directory cleared.")
# Create a button to clear the work directory
if st.button("Clear work directory"):
    clear_work_dir()


def save_uploaded_file(uploadedfile):
  with open(os.path.join("work_dir",uploadedfile.name),"wb") as f:
     f.write(uploadedfile.getbuffer())
  return st.success("Saved file :{} in work_dir".format(uploadedfile.name))

uploaded_file = st.file_uploader("Choose a file to upload to work directory")
if uploaded_file:
    additional_instructions = f"use only the uploaded local file {uploaded_file.name} for the task"
    # Apply Function here
    save_uploaded_file(uploaded_file)
else:
    additional_instructions = ""

# Create a code executor agent that uses docker to execute the code from code writer and surface back the result
code_executor_agent = TrackableConversableAgent(
    "code_executor",
    llm_config=False,  # Turn off LLM for this agent.
    code_execution_config={"executor": executor},  # Use the docker command line code executor.
    human_input_mode="NEVER",  # Always take human input for this agent for safety.
)

code_writer_system_message=f"""You are a helpful AI assistant and today is {get_today_date()}.
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
            If it is a data analysis task, output the result in a markdown table or a chart whereever possible.
            {additional_instructions}
            Reply \"TERMINATE\" in the end when everything is done."""

# Create a code writer agent that will be used to solve the tasks by writing code 
code_writer_agent = TrackableConversableAgent(
    "code_writer_agent",
    system_message=code_writer_system_message,
    llm_config=llm_config,
    code_execution_config=False,  # Turn off code execution for this agent.
    max_consecutive_auto_reply=20,
    human_input_mode="NEVER",
)
if 'chat_initiated' not in st.session_state:
    st.session_state.chat_initiated = False

chat_result = None

# Creating a Streamlit container to hold the chat messages and the input 
with st.container():

    # Create a chat input for the user to type in
    user_input = st.chat_input("Give me a task...")
    # If the user input is not empty, we will initiate the chat
    if user_input:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def initiate_chat():
            try:
                chat_result = code_executor_agent.initiate_chat(
                    code_writer_agent,
                    message=user_input,
                    max_consecutive_auto_reply=10,
                    is_termination_msg=lambda x: x.get("content", "").strip().endswith("TERMINATE"),
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")
        
        loop.run_until_complete(initiate_chat())
        loop.close()
        executor.stop()

if st.session_state.chat_initiated:
    st.write(chat_result)
        
