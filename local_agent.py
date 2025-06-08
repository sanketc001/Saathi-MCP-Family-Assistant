from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.agent import ReActAgent
import asyncio
# import nest_asyncio
# nest_asyncio.apply()
from llama_index.core import StorageContext, load_index_from_storage
import os


Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
# Settings.llm = Ollama(model="llama3", request_timeout=30.0)
Settings.llm = Ollama(model="granite3.2-vision", request_timeout=30.0)

required_exts = [".txt", ".md", ".pdf", ".docx", ".jpg", ".png"]
documents = SimpleDirectoryReader("./files/", required_exts=required_exts, recursive=True).load_data()
print(f"Loaded {len(documents)} docs")
# print(f"Documents: {documents}")

# if os.path.exists("storage"):
#     storage_context = StorageContext.from_defaults(persist_dir="storage")
#     index = load_index_from_storage(storage_context,embed_model=Settings.embed_model,)
#     query_engine = index.as_query_engine(llm=Settings.llm,)
# else:
index = VectorStoreIndex.from_documents(documents,embed_model=Settings.embed_model)
query_engine = index.as_query_engine(llm=Settings.llm)
chat_engine = index.as_chat_engine(llm=Settings.llm)
retrieve_engine = index.as_retriever(llm=Settings.llm)
# print(query_engine.query("Tell me what you know about Sanket"))
# print(chat_engine.chat("What documents do I have?"))
print(retrieve_engine.retrieve("What documents do I have about Sanket?"))

def search_documents(query: str) -> str:
    """Useful for answering natural language questions about any personal files you have."""
    response = query_engine.query(query)
    return str(response)

def analyze_image(image_path: str, question: str = "Describe this image") -> str:
    """Useful for analyzing or extracting insights from an image file."""
    with open(image_path, "rb") as img_file:
        image_bytes = img_file.read()
    response = Settings.llm.complete(prompt=question,image=image_bytes,)
    return response


# Create an enhanced workflow with both tools
agent = AgentWorkflow.from_tools_or_functions([search_documents, analyze_image],llm=Settings.llm,
    system_prompt="""
You are an assistant that helps users find information and insights from their files and images.
You can:
- Search documents when the user asks questions about their files.
- Analyze images if the user provides an image and asks about it.
Decide the correct tool based on the task.
""",)




async def main():
    """Main function to run the agent with the provided query."""
    while True:
        query = input("Ask a question (or type 'exit' to quit): ").strip()
        if query.lower() == 'exit':
            break
        response = await agent.run(query)
        print(f"Running agent with input: {query}\nResponse: {response}")
        print(response.)

    return response


# Run the agent
if __name__ == "__main__":
    asyncio.run(main())
    index.storage_context.persist("storage")