# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description: agentica integrated llamaindex db demo

pip install llamaindex
"""

import sys

sys.path.append('..')
from agentica import Assistant

from agentica.knowledge.llamaindex import LlamaIndexKnowledgeBase
from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.node_parser import SentenceSplitter

# Define the path to the document to be loaded into the knowledge base
file_path = "data/news_docs.txt"

documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

splitter = SentenceSplitter(chunk_size=1024)

nodes = splitter.get_nodes_from_documents(documents)

storage_context = StorageContext.from_defaults()

index = VectorStoreIndex(nodes=nodes, storage_context=storage_context)

retriever = VectorIndexRetriever(index)

# Create a knowledge base from the vector store
knowledge_base = LlamaIndexKnowledgeBase(retriever=retriever)

# Create an assistant with the knowledge base
assistant = Assistant(knowledge_base=knowledge_base, search_knowledge=True, debug_mode=True, show_tool_calls=True)

# Use the assistant to ask a question and print a response.
r = assistant.run("2023年全国田径锦标赛在哪里举办的?")
print("".join(r))
