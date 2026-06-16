import uuid
from langchain_core.messages import HumanMessage
from graph.builder import app_graph

session_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": session_id}}

print(f"Session {session_id} started. (Ctrl+C to exit)")

while True:
    try:
        user_input = input("You: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
        break

    if not user_input:
        continue
    if user_input.lower() in {"sair", "exit", "quit"}:
        break

    result = app_graph.invoke(
        {"messages": [HumanMessage(content=user_input)]}, config=config
    )

    reply = result["messages"][-1].content
    print(f"Assistant: {reply}")
