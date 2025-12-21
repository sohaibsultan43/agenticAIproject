"""
Memory System for ScholarSync
Implements Session, Context, and Running Memory using Weaviate
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import weaviate
from weaviate.classes.config import Configure, Property, DataType
import logging

load_dotenv()
logger = logging.getLogger("ScholarSync.memory")

# Weaviate connection
WEAVIATE_URL = os.getenv("WEAVIATE_CLOUD_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")


def get_memory_client():
    """Get Weaviate client for memory operations"""
    return weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
    )


def create_memory_collections():
    """Create all memory collections in Weaviate"""
    client = get_memory_client()
    
    try:
        # 1. Session Memory Collection
        if not client.collections.exists("SessionMemory"):
            client.collections.create(
                name="SessionMemory",
                properties=[
                    Property(name="session_id", data_type=DataType.TEXT),
                    Property(name="messages", data_type=DataType.TEXT),  # JSON string
                    Property(name="created_at", data_type=DataType.DATE),
                    Property(name="last_active", data_type=DataType.DATE),
                    Property(name="papers_ingested", data_type=DataType.TEXT_ARRAY),
                    Property(name="research_topic", data_type=DataType.TEXT),
                ]
            )
            logger.info("Created SessionMemory collection")
        
        # 2. Context Memory Collection
        if not client.collections.exists("ContextMemory"):
            client.collections.create(
                name="ContextMemory",
                properties=[
                    Property(name="session_id", data_type=DataType.TEXT),
                    Property(name="research_interests", data_type=DataType.TEXT_ARRAY),
                    Property(name="agent_usage", data_type=DataType.TEXT),  # JSON string
                    Property(name="query_patterns", data_type=DataType.TEXT),  # JSON string
                    Property(name="updated_at", data_type=DataType.DATE),
                ]
            )
            logger.info("Created ContextMemory collection")
        
        # 3. Task Memory Collection
        if not client.collections.exists("TaskMemory"):
            client.collections.create(
                name="TaskMemory",
                properties=[
                    Property(name="task_id", data_type=DataType.TEXT),
                    Property(name="session_id", data_type=DataType.TEXT),
                    Property(name="task_type", data_type=DataType.TEXT),
                    Property(name="status", data_type=DataType.TEXT),
                    Property(name="steps", data_type=DataType.TEXT),  # JSON string
                    Property(name="created_at", data_type=DataType.DATE),
                ]
            )
            logger.info("Created TaskMemory collection")
        
        logger.info("All memory collections ready")
        
    finally:
        client.close()


# ============= SESSION MEMORY =============

def save_message(session_id: str, role: str, content: str, agent: Optional[str] = None):
    """Save a message to session history"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("SessionMemory")
        
        # Get existing session or create new
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("session_id").equal(session_id),
            limit=1
        )
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if agent:
            message["agent"] = agent
        
        if result.objects:
            # Update existing session
            obj = result.objects[0]
            messages = json.loads(obj.properties.get("messages", "[]"))
            messages.append(message)
            
            collection.data.update(
                uuid=obj.uuid,
                properties={
                    "messages": json.dumps(messages),
                    "last_active": datetime.utcnow()
                }
            )
        else:
            # Create new session
            collection.data.insert(
                properties={
                    "session_id": session_id,
                    "messages": json.dumps([message]),
                    "created_at": datetime.utcnow(),
                    "last_active": datetime.utcnow(),
                    "papers_ingested": [],
                    "research_topic": ""
                }
            )
        
        logger.info(f"Saved message to session {session_id}")
        
    finally:
        client.close()


def get_session_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent messages from session"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("SessionMemory")
        
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("session_id").equal(session_id),
            limit=1
        )
        
        if result.objects:
            messages = json.loads(result.objects[0].properties.get("messages", "[]"))
            return messages[-limit:]  # Return last N messages
        
        return []
        
    finally:
        client.close()


def update_session_papers(session_id: str, papers: List[str]):
    """Update papers ingested in session"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("SessionMemory")
        
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("session_id").equal(session_id),
            limit=1
        )
        
        if result.objects:
            collection.data.update(
                uuid=result.objects[0].uuid,
                properties={"papers_ingested": papers}
            )
        
    finally:
        client.close()


# ============= CONTEXT MEMORY =============

def update_context(session_id: str, agent_used: Optional[str] = None, query: Optional[str] = None):
    """Update user context with usage patterns"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("ContextMemory")
        
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("session_id").equal(session_id),
            limit=1
        )
        
        if result.objects:
            # Update existing context
            obj = result.objects[0]
            agent_usage = json.loads(obj.properties.get("agent_usage", "{}"))
            
            if agent_used:
                agent_usage[agent_used] = agent_usage.get(agent_used, 0) + 1
            
            collection.data.update(
                uuid=obj.uuid,
                properties={
                    "agent_usage": json.dumps(agent_usage),
                    "updated_at": datetime.utcnow()
                }
            )
        else:
            # Create new context
            agent_usage = {agent_used: 1} if agent_used else {}
            
            collection.data.insert(
                properties={
                    "session_id": session_id,
                    "research_interests": [],
                    "agent_usage": json.dumps(agent_usage),
                    "query_patterns": json.dumps({}),
                    "updated_at": datetime.utcnow()
                }
            )
        
    finally:
        client.close()


def get_context(session_id: str) -> Dict[str, Any]:
    """Retrieve user context"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("ContextMemory")
        
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("session_id").equal(session_id),
            limit=1
        )
        
        if result.objects:
            props = result.objects[0].properties
            return {
                "agent_usage": json.loads(props.get("agent_usage", "{}")),
                "research_interests": props.get("research_interests", []),
                "query_patterns": json.loads(props.get("query_patterns", "{}"))
            }
        
        return {"agent_usage": {}, "research_interests": [], "query_patterns": {}}
        
    finally:
        client.close()


# ============= TASK MEMORY =============

def create_task(session_id: str, task_type: str, task_id: Optional[str] = None) -> str:
    """Create a new multi-step task"""
    if not task_id:
        task_id = f"task_{session_id}_{datetime.utcnow().timestamp()}"
    
    client = get_memory_client()
    
    try:
        collection = client.collections.get("TaskMemory")
        
        collection.data.insert(
            properties={
                "task_id": task_id,
                "session_id": session_id,
                "task_type": task_type,
                "status": "in_progress",
                "steps": json.dumps([]),
                "created_at": datetime.utcnow()
            }
        )
        
        logger.info(f"Created task {task_id}")
        return task_id
        
    finally:
        client.close()


def update_task_step(task_id: str, step_data: Dict[str, Any]):
    """Add or update a task step"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("TaskMemory")
        
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("task_id").equal(task_id),
            limit=1
        )
        
        if result.objects:
            obj = result.objects[0]
            steps = json.loads(obj.properties.get("steps", "[]"))
            steps.append(step_data)
            
            collection.data.update(
                uuid=obj.uuid,
                properties={"steps": json.dumps(steps)}
            )
        
    finally:
        client.close()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status and steps"""
    client = get_memory_client()
    
    try:
        collection = client.collections.get("TaskMemory")
        
        result = collection.query.fetch_objects(
            filters=weaviate.classes.query.Filter.by_property("task_id").equal(task_id),
            limit=1
        )
        
        if result.objects:
            props = result.objects[0].properties
            return {
                "task_id": props["task_id"],
                "session_id": props["session_id"],
                "task_type": props["task_type"],
                "status": props["status"],
                "steps": json.loads(props.get("steps", "[]")),
                "created_at": props["created_at"]
            }
        
        return None
        
    finally:
        client.close()


if __name__ == "__main__":
    # Initialize collections
    print("Creating memory collections...")
    create_memory_collections()
    print("Memory system ready!")
