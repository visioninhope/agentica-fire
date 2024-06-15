from rich.pretty import pprint
import sys

sys.path.append('..')
from actionflow.assistant import Assistant, AssistantMemory
from actionflow import AzureOpenAILLM

llm = AzureOpenAILLM()
assistant = Assistant(llm=llm)

# -*- Print a response
assistant.print_response("Share a 5 word horror story.")
assistant.print_response("What's the weather like today?")
assistant.print_response("我前面问了些啥")

# -*- Get the memory
memory: AssistantMemory = assistant.memory

# -*- Print Chat History
print("============ Chat History ============")
pprint(memory.chat_history)

# -*- Print LLM Messages
print("============ LLM Messages ============")
pprint(memory.llm_messages)