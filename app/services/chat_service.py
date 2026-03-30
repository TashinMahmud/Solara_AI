from sqlalchemy.orm import Session
from app.model.models import User, Session as DBSession, Message, Plan
from app.schemas.chat import (
    ChatRequest, ChatResponse, Question,
    DestinationCard, HotelCard, PackageCard, FollowUpQuestion
)
from typing import Dict, List
import json
import re
import requests
from bs4 import BeautifulSoup
import html2text
from duckduckgo_search import DDGS
from anthropic import Anthropic
from app.core.config import settings

class ChatService:
    def __init__(self):
        self.client = Anthropic(api_key=settings.claude_api_key)
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_tables = False
        self.html_converter.body_width = 0  # Don't wrap text

        # General conversational flow for AI search
        self.flow = [
            {"key": "query", "question": "What would you like me to search for?", "required": True},
        ]

    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search the web using DuckDuckGo and return results with content."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))
                return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def fetch_and_convert_to_markdown(self, url: str) -> str:
        """Fetch a webpage and convert it to markdown."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Convert HTML to markdown
            markdown = self.html_converter.handle(response.text)

            # Clean up the markdown
            lines = markdown.split('\n')
            cleaned_lines = []

            for line in lines:
                # Skip very long lines (likely navigation or ads)
                if len(line) > 1000:
                    continue
                # Skip lines that are just links or images
                if line.strip().startswith('![') or line.strip() == '':
                    continue
                cleaned_lines.append(line)

            return '\n'.join(cleaned_lines[:50])  # Limit to first 50 lines

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def perform_ai_search(self, query: str) -> Dict:
        """Perform AI-powered search similar to Perplexity."""
        # First, search the web
        search_results = self.search_web(query, num_results=3)

        if not search_results:
            return {
                "answer": "I couldn't find any search results for that query. Please try rephrasing your question.",
                "sources": [],
                "follow_up_questions": []
            }

        # Fetch content from top results
        sources_content = []
        sources = []

        for i, result in enumerate(search_results[:3]):
            url = result.get('href', '')
            title = result.get('title', 'Unknown')
            body = result.get('body', '')

            if url:
                # Try to fetch full content
                full_content = self.fetch_and_convert_to_markdown(url)
                if full_content:
                    sources_content.append(f"Source {i+1} ({title}):\n{full_content}")
                else:
                    sources_content.append(f"Source {i+1} ({title}):\n{body}")

                sources.append({
                    "title": title,
                    "url": url,
                    "snippet": body[:200] + "..." if len(body) > 200 else body
                })

        # Combine all source content
        combined_content = "\n\n".join(sources_content)

        # Use Claude to generate a comprehensive answer
        system_prompt = """You are a helpful AI search assistant like Perplexity. 
        Based on the web search results provided, give a comprehensive, accurate answer to the user's query.
        Be conversational, informative, and cite your sources when relevant.
        If the information isn't available in the sources, say so clearly.
        Keep your response natural and engaging."""

        user_prompt = f"""
Query: {query}

Search Results:
{combined_content}

Please provide a comprehensive answer based on these search results. Be conversational and cite sources when you use information from them.
"""

        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        answer = response.content[0].text.strip()

        # Generate follow-up questions
        follow_up_prompt = f"""
Based on this query: "{query}"
And this answer: "{answer[:200]}..."

Suggest 2-3 relevant follow-up questions the user might ask next.
Return them as a JSON array of strings.
"""

        follow_up_response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            system="Generate relevant follow-up questions based on the conversation.",
            messages=[{"role": "user", "content": follow_up_prompt}]
        )

        try:
            follow_up_questions = json.loads(follow_up_response.content[0].text.strip())
            if not isinstance(follow_up_questions, list):
                follow_up_questions = []
        except:
            follow_up_questions = []

        return {
            "answer": answer,
            "sources": sources,
            "follow_up_questions": follow_up_questions
        }

    def process_message(self, db: Session, request: ChatRequest) -> ChatResponse:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            user = User(id=request.user_id)
            db.add(user)
            db.commit()

        session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
        if not session:
            session = DBSession(id=request.session_id, user_id=request.user_id)
            db.add(session)
            db.commit()

        user_message = Message(session_id=request.session_id, content=request.message, is_bot=False)
        db.add(user_message)
        db.commit()

        messages = db.query(Message).filter(Message.session_id == request.session_id).order_by(Message.created_at).all()
        history = {msg.content for msg in messages if not msg.is_bot}

        collected_info = self.extract_info(history)
        next_questions = self.get_next_questions(collected_info)

        plan_generated = False
        plan_summary = None
        destinations = []
        hotels = []
        packages = []
        follow_ups = []
        sources = []

        # Check if we have a query to search for
        if collected_info.get("query"):
            search_result = self.perform_ai_search(collected_info["query"])
            answer = search_result["answer"]
            sources = search_result["sources"]
            follow_ups = [FollowUpQuestion(question=q, suggestions=[]) for q in search_result["follow_up_questions"]]
            plan_generated = True
            plan_summary = f"Search query: {collected_info['query']}"
        else:
            answer = self.generate_conversational_response(collected_info, next_questions)

        bot_message = Message(session_id=request.session_id, content=answer, is_bot=True)
        db.add(bot_message)
        db.commit()

        if plan_generated:
            plan = Plan(session_id=request.session_id, summary=plan_summary, details=json.dumps(collected_info))
            db.add(plan)
            db.commit()

        return ChatResponse(
            answer=answer,
            conversational_text=answer,
            destinations=destinations,
            hotels=hotels,
            packages=packages,
            follow_up_questions=follow_ups,
            sources=sources,
            plan_generated=plan_generated,
            plan_summary=plan_summary
        )

    def extract_info(self, history: set) -> Dict[str, str]:
        info: Dict[str, str] = {}

        # Parse key:value lines first
        for msg in history:
            if ":" in msg:
                parts = [p.strip() for p in msg.split(":", 1)]
                if len(parts) == 2:
                    key_text, value_text = parts
                    for item in self.flow:
                        if item["key"] == key_text.lower():
                            info[item["key"]] = value_text

        # For general search queries, treat any message as a potential query
        for msg in history:
            if msg and len(msg.strip()) > 3 and "query" not in info:
                # Skip if it looks like a response or system message
                if not msg.startswith(("Thanks", "Great", "I found", "Here's", "Based on")):
                    info["query"] = msg.strip()

        return info

    def get_next_questions(self, collected_info: Dict[str, str]) -> List[Question]:
        questions: List[Question] = []
        for item in self.flow:
            if item["key"] not in collected_info and item["required"]:
                questions.append(Question(question=item["question"], key=item["key"]))
        return questions[:1]

    def generate_conversational_response(self, info: Dict[str, str], next_questions: List[Question]) -> str:
        if not info:
            return "👋 Hi! I'm your AI search assistant. I can help you search the web and answer questions about any topic. What would you like to know?"
        elif next_questions:
            return next_questions[0].question
        return "I'm ready to help! What would you like me to search for?"

    def can_generate_plan(self, info: Dict[str, str]) -> bool:
        # For search engine, we can "generate" a response as soon as we have a query
        return "query" in info and len(info["query"].strip()) > 0
