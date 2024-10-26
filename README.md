# MultiAgent Demos

This repository contains various demos showcasing the use of multiple agents in different applications. The demos utilize technologies such as Azure OpenAI, Streamlit, and various Python libraries to create interactive and intelligent applications.


### Key Files and Directories

- **AutoGenMultiAgents/**: Contains demos related to multi-agent applications.
  - **Multi_Agent_App.py**: Main application file for running multi-agent demos.
  - **pages/**: Contains individual pages for different functionalities.
    - **1 Run_Virtual_Focus_Group.py**: Script to run a virtual focus group.
    - **Analyze_Final_Results.py**: Script to analyze the final results of the focus group.
  - **docs/**: Contains documentation and data files.
    - **chat_summary.txt**: Summary of the chat from the focus group.
    - **final_analysis.md**: Final analysis of the focus group.
    - **personas.json**: JSON file containing persona data.
  - **demographics_dict.py**: Contains demographic data for personas.
  - **persona_handler.py**: Handles persona-related functionalities.

- **AutoGenTwoAgents/**: Contains demos related to two-agent applications.
  - **coderapp.py**: Application for code interpretation.
  - **groupchatapp.py**: Application for group chat.
  - **multitoolsapp.py**: Application demonstrating multiple tools.
  - **two_agents_app.py**: Main application file for running two-agent demos.

- **coder_output/**: Directory for storing output from the coder application.

- **requirements.txt**: List of dependencies required to run the applications.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Azure account with Cognitive Services resource
- Required Python packages (listed in `requirements.txt`)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/multiagent-demos.git
    cd multiagent-demos
    ```

2. Create and activate a virtual environment:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up environment variables:
    - Create a `.env` file in the root directory and add your Azure credentials and other necessary environment variables.

### Running the Applications

#### Multi-Agent Application

To run the multi-agent application, navigate to the `AutoGenMultiAgents` directory and run the `Multi_Agent_App.py` script using Streamlit:

```sh
cd AutoGenMultiAgents
streamlit run Multi_Agent_App.py

cd AutoGenTwoAgents
streamlit run two_agents_app.py