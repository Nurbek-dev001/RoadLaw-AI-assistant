#!/usr/bin/env python3
"""
ПДД AI Kazakhstan - FastAPI Backend
Справочный сервис по правилам дорожного движения
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables
load_dotenv()

print("Starting FastAPI backend...")
print(f"Python: {sys.version}")
print(f"Working directory: {os.getcwd()}")

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    print("✅ FastAPI imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Try to import Chroma
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
    print("✅ Chroma available")
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️  Chroma not available - using fallback data")

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    print("✅ OpenAI available")
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not available - no AI responses")

# Create FastAPI app
app = FastAPI(
    title="🚗 ПДД AI Kazakhstan",
    description="RAG-based traffic rules assistant",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Question(BaseModel):
    question: str
    language: str = "ru"

class Answer(BaseModel):
    answer: str
    sources: list
    confidence: float

# Load sample data
def load_sample_data():
    """Load sample ПДД data from JSON"""
    data_path = Path(__file__).parent.parent / "data" / "pdd_sample.json"
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('rules', [])
    except Exception as e:
        print(f"⚠️  Error loading data: {e}")
        return []

# Load data on startup
PDD_DATA = load_sample_data()
print(f"✅ Loaded {len(PDD_DATA)} ПДД rules")

# Initialize cache for frequently asked questions
answer_cache = {}
cache_hits = 0
cache_misses = 0

def get_cache_key(question: str) -> str:
    """Generate cache key from question"""
    return hashlib.md5(question.lower().strip().encode()).hexdigest()

# Initialize Chroma
client = None
if CHROMA_AVAILABLE:
    try:
        VECTOR_DB_PATH = os.getenv("CHROMA_DB_PATH", "./vector_db/chroma_data")
        client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=VECTOR_DB_PATH,
            anonymized_telemetry=False
        ))
        print(f"✅ Chroma initialized at {VECTOR_DB_PATH}")
    except Exception as e:
        print(f"⚠️  Error initializing Chroma: {e}")
        client = None

# Initialize OpenAI
openai_client = None
if OPENAI_AVAILABLE:
    try:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key and not api_key.startswith("sk-your"):
            openai_client = OpenAI(api_key=api_key)
            print("✅ OpenAI initialized")
        else:
            print("⚠️  OpenAI API key not configured")
    except Exception as e:
        print(f"⚠️  Error initializing OpenAI: {e}")

def simple_search(question: str, n_results: int = 3):
    """Simple keyword-based search in ПДД data"""
    # Convert to lowercase for comparison
    q_lower = question.lower()
    
    results = []
    for rule in PDD_DATA:
        # Check if keywords match
        keywords = rule.get('keywords', [])
        title = rule.get('title', '').lower()
        content = rule.get('content', '').lower()
        
        # Calculate relevance
        relevance = 0
        for keyword in keywords:
            if keyword.lower() in q_lower:
                relevance += 0.3
        
        if any(word in q_lower for word in title.split()):
            relevance += 0.5
        
        if any(word in q_lower for word in content.split()):
            relevance += 0.2
        
        if relevance > 0:
            results.append({
                'rule': rule,
                'relevance': min(relevance, 1.0)
            })
    
    # Sort by relevance and return top n
    results = sorted(results, key=lambda x: x['relevance'], reverse=True)
    return results[:n_results]

def chroma_search(question: str, n_results: int = 3):
    """Search using Chroma vector database"""
    if not client:
        return []
    
    try:
        collection = client.get_collection(name="pdd_rules")
        query_results = collection.query(
            query_texts=[question],
            n_results=n_results
        )
        
        results = []
        if query_results['documents'] and len(query_results['documents']) > 0:
            for i, doc in enumerate(query_results['documents'][0]):
                # Find matching rule in PDD_DATA
                for rule in PDD_DATA:
                    if rule['content'] in doc or rule['title'] in doc:
                        distance = query_results['distances'][0][i] if query_results['distances'] else 1.0
                        results.append({
                            'rule': rule,
                            'relevance': 1 - min(distance, 1.0)
                        })
                        break
        
        return results
    except Exception as e:
        print(f"Chroma search error: {e}")
        return []

def search_pdd(question: str, n_results: int = 3):
    """Search ПДД data - try Chroma first, fallback to simple search"""
    # Try Chroma first
    if CHROMA_AVAILABLE:
        results = chroma_search(question, n_results)
        if results:
            return results
    
    # Fallback to simple search
    return simple_search(question, n_results)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "service": "🚗 ПДД AI Kazakhstan",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/ask (POST)",
            "/docs"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected" if client else "fallback",
        "documents": len(PDD_DATA),
        "ai_enabled": openai_client is not None
    }

@app.get("/metrics")
async def get_metrics() -> dict:
    """Get caching and performance metrics"""
    total_queries = cache_hits + cache_misses
    hit_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0
    
    return {
        "total_queries": total_queries,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "hit_rate_percent": round(hit_rate, 2),
        "cache_size": len(answer_cache)
    }

@app.post("/ask", response_model=Answer)
async def ask_question(question_data: Question) -> Answer:
    """Main endpoint: Ask a question about ПДД RK"""
    global cache_hits, cache_misses
    
    question = question_data.question.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question too long (max 500 chars)")
    
    # Check cache
    cache_key = get_cache_key(question)
    if cache_key in answer_cache:
        cache_hits += 1
        print(f"✅ Cache HIT for: {question[:50]}... (hits: {cache_hits})")
        return answer_cache[cache_key]
    
    cache_misses += 1
    
    try:
        # Search for relevant ПДД info
        search_results = search_pdd(question, n_results=3)
        
        if not search_results:
            result = Answer(
                answer="В базе данных нет информации по этому вопросу. Пожалуйста, уточните вопрос или обратитесь к официальным источникам ПДД.",
                sources=[],
                confidence=0.0
            )
            answer_cache[cache_key] = result
            return result
        
        # Prepare sources
        sources = []
        context_parts = []
        
        total_relevance = 0
        for result in search_results:
            rule = result['rule']
            relevance = result['relevance']
            
            sources.append({
                'section': rule.get('section', 'Неизвестный раздел'),
                'id': rule.get('id', ''),
                'title': rule.get('title', ''),
                'relevance': relevance
            })
            
            context_parts.append(f"{rule.get('title', '')}: {rule.get('content', '')}")
            total_relevance += relevance
        
        # Generate answer
        answer = None
        if openai_client:
            try:
                system_prompt = """Ты помощник по ПДД Республики Казахстан.
Отвечай ТОЛЬКО на основе предоставленных документов.
Объясняй правила простым языком.
Всегда указывай конкретный пункт.
Ответ должен быть кратким (1-3 предложения)."""
                
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Контекст ПДД:\n{chr(10).join(context_parts)}\n\nВопрос: {question}"}
                    ],
                    temperature=0.2,
                    max_tokens=300,
                    timeout=10
                )
                answer = response.choices[0].message.content
                print(f"✅ OpenAI response for: {question[:50]}...")
                
            except Exception as e:
                error_msg = str(e)
                if "insufficient_quota" in error_msg:
                    print(f"⚠️  OpenAI quota exceeded, using fallback")
                else:
                    print(f"⚠️  OpenAI error: {error_msg}")
                # Fallback to base information
                answer = None
        
        # Fallback answer if OpenAI failed or not available
        if not answer:
            answer = f"Найдено в ПДД РК:\n\n{chr(10).join(context_parts)}"
        
        # Calculate confidence
        confidence = min(total_relevance / len(search_results), 1.0) if search_results else 0.0
        
        result = Answer(
            answer=answer,
            sources=sources,
            confidence=confidence
        )
        
        # Cache the result
        answer_cache[cache_key] = result
        
        return result
        
    except Exception as e:
        print(f"Error in /ask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs")
async def docs():
    """API Documentation"""
    return {
        "title": "ПДД AI Kazakhstan API",
        "version": "0.1.0",
        "endpoints": {
            "GET /": "Root endpoint - service info",
            "GET /health": "Health check",
            "POST /ask": "Ask a question about ПДД",
            "GET /docs": "This documentation"
        },
        "example_request": {
            "question": "Кто уступает на круге?",
            "language": "ru"
        },
        "example_response": {
            "answer": "Согласно ПДД РК...",
            "sources": [
                {
                    "section": "13. Проезд перекрестков",
                    "id": "13.7",
                    "title": "Приоритет на круговом движении",
                    "relevance": 0.95
                }
            ],
            "confidence": 0.92
        }
    }

if __name__ == "__main__":
    print("Starting server on 0.0.0.0:8000...")
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)
