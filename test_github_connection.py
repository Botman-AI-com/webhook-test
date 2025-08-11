#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión con GitHub
"""

import os
from dotenv import load_dotenv
from github import Github
import sys

def test_github_connection():
    """Test GitHub API connection"""
    load_dotenv()
    
    token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('OWNER')
    repo_name = os.getenv('REPO')
    
    if not token:
        print("❌ GITHUB_TOKEN not found in .env file")
        return False
    
    if not token.startswith('ghp_') and not token.startswith('github_pat_'):
        print("⚠️  Warning: GITHUB_TOKEN doesn't look like a valid token")
        print("   Expected format: ghp_xxxxxxxxxxxx or github_pat_xxxxxxxxxxxx")
    
    try:
        print("🔍 Testing GitHub connection...")
        github_client = Github(token)
        
        # Test authentication
        user = github_client.get_user()
        print(f"✅ Authenticated as: {user.login}")
        print(f"   Rate limit: {github_client.get_rate_limit().core.remaining}/5000")
        
        # Test repository access
        if owner and repo_name:
            print(f"\n📁 Testing repository access: {owner}/{repo_name}")
            try:
                repo = github_client.get_repo(f"{owner}/{repo_name}")
                print(f"✅ Repository found: {repo.full_name}")
                print(f"   Description: {repo.description or 'No description'}")
                print(f"   Default branch: {repo.default_branch}")
                print(f"   Last updated: {repo.updated_at}")
                
                # Test recent commits
                commits = list(repo.get_commits().get_page(0))
                if commits:
                    latest_commit = commits[0]
                    print(f"   Latest commit: {latest_commit.sha[:8]} - {latest_commit.commit.message.split(chr(10))[0]}")
                    
                    # Test file access
                    try:
                        contents = repo.get_contents("", ref=latest_commit.sha)
                        code_files = [f.path for f in contents if f.path.endswith(('.py', '.js', '.ts', '.java'))]
                        print(f"   Code files found: {len(code_files)}")
                        if code_files:
                            print(f"   Examples: {', '.join(code_files[:3])}")
                    except Exception as e:
                        print(f"   ⚠️  Could not access repository contents: {e}")
                
            except Exception as e:
                print(f"❌ Repository access failed: {e}")
                return False
        
        print("\n🎉 GitHub connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ GitHub connection failed: {e}")
        print("\n💡 Make sure your token has these permissions:")
        print("   - repo (Full control of private repositories)")
        print("   - read:org (Read org and team membership)")
        return False

def test_neo4j_connection():
    """Test Neo4j connection"""
    load_dotenv()
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password123')
        
        print(f"\n🔍 Testing Neo4j connection to {uri}...")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            result = session.run("RETURN 'Hello Neo4j!' as message")
            record = result.single()
            print(f"✅ Neo4j connected: {record['message']}")
            
            # Test basic query
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            count = result.single()['node_count']
            print(f"   Current nodes in database: {count}")
        
        driver.close()
        return True
        
    except ImportError:
        print("❌ neo4j package not installed. Run: pip install neo4j")
        return False
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        print("\n💡 Make sure Neo4j is running:")
        print("   docker-compose up neo4j -d")
        return False

if __name__ == "__main__":
    print("🧪 Testing GitHub-Neo4j Integration Setup\n")
    
    github_ok = test_github_connection()
    neo4j_ok = test_neo4j_connection()
    
    print("\n" + "="*50)
    if github_ok and neo4j_ok:
        print("🎉 All tests passed! Ready to sync GitHub to Neo4j")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check configuration above.")
        sys.exit(1)