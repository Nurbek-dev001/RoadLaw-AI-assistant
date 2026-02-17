#!/usr/bin/env python3
"""
Test script for PDD AI Backend
Tests the /ask endpoint with various questions
"""

import requests
import json

BACKEND_URL = "http://localhost:8000"

def test_ask_endpoint(question):
    """Test the /ask endpoint"""
    print(f"\n{'='*60}")
    print(f"❓ Question: {question}")
    print('='*60)
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": question, "language": "ru"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"\n📝 Answer:")
            print(f"{data.get('answer', 'No answer')}")
            
            print(f"\n📋 Sources:")
            for source in data.get('sources', []):
                print(f"  - {source.get('section')} ({source.get('id')})")
                print(f"    {source.get('title')}")
                print(f"    Relevance: {source.get('relevance'):.0%}")
            
            print(f"\n📊 Confidence: {data.get('confidence', 0):.0%}")
            
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health():
    """Test the /health endpoint"""
    print("\n" + "="*60)
    print("Testing /health endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        data = response.json()
        print(f"✅ Server Status: {data.get('status')}")
        print(f"📊 Database: {data.get('database')}")
        print(f"📚 Documents: {data.get('documents')}")
        print(f"🤖 AI Enabled: {data.get('ai_enabled')}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n🚗 PDD AI Backend Test Suite")
    print(f"Backend URL: {BACKEND_URL}\n")
    
    # Test health
    test_health()
    
    # Test various questions
    test_questions = [
        "Кто уступает на круге?",
        "Какой штраф за красный свет?",
        "Можно ли обгонять на пешеходном переходе?",
        "Скорость в городе",
        "Правила остановки"
    ]
    
    print("\n" + "="*60)
    print("Testing Question Processing")
    print("="*60)
    
    for question in test_questions:
        test_ask_endpoint(question)
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")
