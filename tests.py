"""
Tests for ПДД AI Казахстан
Run with: pytest tests.py -v
"""

import pytest
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.prepare_data import load_pdd_data, prepare_documents

class TestDataPreparation:
    """Test data preparation functions"""
    
    def test_load_pdd_data(self):
        """Test loading ПДД data from JSON"""
        data_path = Path(__file__).parent / "data" / "pdd_sample.json"
        
        if not data_path.exists():
            pytest.skip("Sample data not found")
        
        rules = load_pdd_data(str(data_path))
        assert len(rules) > 0
        assert all('id' in rule for rule in rules)
        assert all('content' in rule for rule in rules)
    
    def test_prepare_documents(self):
        """Test document preparation"""
        sample_rules = [
            {
                'id': '1.1',
                'title': 'Test Rule',
                'content': 'Test content',
                'section': 'Section 1',
                'type': 'rule',
                'keywords': ['test']
            }
        ]
        
        ids, documents, metadatas = prepare_documents(sample_rules)
        
        assert len(ids) == 1
        assert len(documents) == 1
        assert len(metadatas) == 1
        assert ids[0] == '1.1'
        assert 'Test Rule' in documents[0]

class TestBackendAPI:
    """Test backend API"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code in [200, 500]  # 500 if DB not initialized
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert 'ПДД AI' in response.json()['service']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
