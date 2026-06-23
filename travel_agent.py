import os
import agentc
import agentc_langgraph.agent
from agentc_langgraph.agent import State as AgentState
from agentc_core.activity.models.content import UserContent, AssistantContent 
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()

class TravelAssistant(agentc_langgraph.agent.ReActAgent):
    def __init__(self, catalog: agentc.Catalog, span: agentc.Span, **kwargs):
        import langchain_openai
        chat_model = langchain_openai.ChatOpenAI(model="gpt-4o", temperature=0)
        self.memory = MemorySaver()
        super().__init__(
            chat_model=chat_model,
            catalog=catalog,
            span=span,
            prompt_name="travel_agent"
        )

    def _stream(self, span: agentc.Span, state: AgentState, config):
        agent = self.create_react_agent(span, checkpointer=self.memory)
        for chunk in agent.stream(input=state, config=config, stream_mode="values"):
            yield chunk


def run_app():
    os.system('cls' if os.name == 'nt' else 'clear')

    catalog = agentc.Catalog()

    with catalog.Span(name="terminal_session") as root_span:
        my_agent = TravelAssistant(catalog=catalog, span=root_span)
        print("Governed Agent Active | Launching...")

        config = {"recursion_limit": 25, "configurable": {"thread_id": "traveler_1"}}

        while True:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit': break

            # Log the USER message to the tracer
            root_span.log(content=UserContent(value=user_input))

            state: AgentState = {"messages": [HumanMessage(content=user_input)]}

            final_message = None
            for chunk in my_agent._stream(span=root_span, state=state, config=config):
                message = chunk["messages"][-1]
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        print(f"\n  [TOOL CALL]: {tool_call['name']}({tool_call['args']})")
                elif message.type == "ai" and not getattr(message, "tool_calls", None):
                    final_message = message

            if final_message:
                print(f"\nAgent: {final_message.content}")
                # Log the ASSISTANT message to the tracer
                root_span.log(content=AssistantContent(value=final_message.content))

if __name__ == "__main__":
    run_app()
