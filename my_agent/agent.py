from google.adk.agents.llm_agent import Agent
from datetime import datetime
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    time = datetime.now().strftime("%H:%M:%S")
    return {"status": "success", "city": city, "time": time}

root_agent = Agent(
    model='gemini-2.5-flash',
    name='time_agent',
    description="Tells the current time in a specified city.",
    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
    tools=[get_current_time]
)

