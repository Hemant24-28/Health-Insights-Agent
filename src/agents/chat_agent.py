import streamlit as st
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import logging

logger = logging.getLogger(__name__)

class ChatAgent:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        self.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        self.model_name = "gemini-3.8-flash"

    def initialize_vector_store(self, text_content):
        """Create vector store from text content."""
        if not text_content or text_content.strip() == "":
            # Create a minimal vector store with a placeholder
            text_content = "No report context available."

        texts = self.text_splitter.split_text(text_content)
        if not texts:
            # If splitting results in empty list, add at least one text
            texts = [text_content]

        vectorstore = FAISS.from_texts(texts, self.embeddings)
        return vectorstore

    def _format_chat_history(self, chat_history):
        """Format chat history for the Gemini API."""
        messages = []
        for msg in chat_history:
            role = msg.get("role")
            if role in ("user", "assistant"):
                messages.append(
                    {
                        "role": "model" if role == "assistant" else "user",
                        "parts": [{"text": msg["content"]}],
                    }
                )
        return messages

    def _contextualize_query(self, query, chat_history):
        """Reformulate query considering chat history."""
        if not chat_history:
            return query

        # Build context from recent chat history
        recent_history = [
            msg for msg in chat_history if msg.get("role") in ("user", "assistant")
        ][-4:]  # Last 2 exchanges
        history_text = "\n".join(
            [
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in recent_history
            ]
        )

        contextualize_prompt = f"""Given a chat history and the latest user question, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is.

Chat History:
{history_text}

Latest User Question: {query}

Standalone Question:"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contextualize_prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You reformulate questions to be standalone.",
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )
            return response.text.strip() if response.text else query
        except Exception as exc:
            logger.warning("Gemini query contextualization failed: %s", exc)
            return query  # Fallback to original query

    def get_response(self, query, vectorstore, chat_history=None):
        """Get response using RAG."""
        if chat_history is None:
            chat_history = []

        # 1. Contextualize query based on chat history
        contextualized_query = self._contextualize_query(query, chat_history)

        # 2. Retrieve relevant documents
        try:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            docs = retriever.get_relevant_documents(contextualized_query)
            context = "\n\n".join([doc.page_content for doc in docs])

            # If context is just placeholder text, set to empty
            if context.strip() == "No report context available.":
                context = ""
        except Exception:
            # If retrieval fails, proceed without context
            context = ""

        # 3. Build prompt with context and chat history
        qa_system_prompt = (
            "You are an assistant for question-answering tasks. "
            "Use the following pieces of retrieved context to answer the question. "
            "If you don't know the answer, just say that you don't know. "
            "Use three sentences maximum and keep the answer concise."
        )

        messages = self._format_chat_history(chat_history[-6:])

        # Add context and current query
        if (
            context
            and context.strip()
            and context.strip() != "No report context available."
        ):
            user_message = f"Context:\n{context}\n\nQuestion: {query}"
        else:
            # No report context available, rely on chat history only
            user_message = f"Question: {query}\n\nNote: No report context is available. Please answer based on the chat history."
        messages.append({"role": "user", "parts": [{"text": user_message}]})

        # 4. Get response from Gemini
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=qa_system_prompt,
                    temperature=0.7,
                    max_output_tokens=500,
                ),
            )
            if not response.text:
                return "Error generating response: Gemini returned no text content."
            return response.text
        except Exception as e:
            return f"Error generating response: {str(e)}"
