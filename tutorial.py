import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama




# Set embedding model
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text")

# Set ollama model
Settings.llm = Ollama(model="gemma3", request_timeout=120.0)



