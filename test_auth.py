#!/usr/bin/env python3
"""Test authentication endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """Test user registration"""
    print("\n1. Testing Registration...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    })
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    return resp.status_code == 200

def test_login():
    """Test user login"""
    print("\n2. Testing Login...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get("access_token") if resp.status_code == 200 else None

def test_auth_chat(token):
    """Test authenticated chat"""
    print("\n3. Testing Authenticated Chat...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/chat", 
        headers=headers,
        json={"message": "Hello! Remember my name is TestUser."})
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

def test_get_me(token):
    """Test get current user"""
    print("\n4. Testing Get Current User...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

def test_unauth_chat():
    """Test unauthenticated chat (backward compatibility)"""
    print("\n5. Testing Unauthenticated Chat (Backward Compatibility)...")
    resp = requests.post(f"{BASE_URL}/chat", json={"message": "Hi there!"})
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Greenie Authentication")
    print("=" * 60)
    
    # Test registration
    test_register()
    
    # Test login and get token
    token = test_login()
    if not token:
        print("\n❌ Login failed. Cannot continue.")
        exit(1)
    
    # Test authenticated endpoints
    test_auth_chat(token)
    test_get_me(token)
    
    # Test backward compatibility
    test_unauth_chat()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
