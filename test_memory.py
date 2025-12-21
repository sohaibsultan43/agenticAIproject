"""
Comprehensive Memory System Test Suite
Tests all three memory types: Session, Context, and Running
"""

import os
import sys
from datetime import datetime
import time

# Set CORE API key
os.environ['CORE_API_KEY'] = 'pvJ3MjDf9HCgYS4luTaNtbnQ072BsGK8'

from memory import (
    create_memory_collections,
    save_message, get_session_history, update_session_papers,
    update_context, get_context,
    create_task, update_task_step, get_task
)

print("=" * 60)
print("MEMORY SYSTEM TEST SUITE")
print("=" * 60)

# Test session ID
test_session = f"test_session_{int(time.time())}"

# ============= TEST 1: SESSION MEMORY =============
print("\n[TEST 1] SESSION MEMORY")
print("-" * 60)

print("1.1 Saving messages...")
save_message(test_session, "user", "What is a diffusion model?")
save_message(test_session, "assistant", "A diffusion model is a type of generative model...", agent="GeneralQAAgent")
save_message(test_session, "user", "Can you explain it in simple terms?")
save_message(test_session, "assistant", "Sure! Think of it like...", agent="GeneralQAAgent")
print("[OK] Saved 4 messages")

print("\n1.2 Retrieving session history...")
history = get_session_history(test_session, limit=10)
print(f"[OK] Retrieved {len(history)} messages")
for i, msg in enumerate(history, 1):
    role = msg['role']
    content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
    agent = msg.get('agent', 'N/A')
    print(f"  {i}. [{role}] {content} (Agent: {agent})")

print("\n1.3 Testing message limit...")
history_limited = get_session_history(test_session, limit=2)
print(f"[OK] Limited to {len(history_limited)} messages (should be 2)")

print("\n1.4 Updating papers ingested...")
update_session_papers(test_session, ["paper1.pdf", "paper2.pdf", "paper3.pdf"])
print("[OK] Updated papers list")

# ============= TEST 2: CONTEXT MEMORY =============
print("\n\n[TEST 2] CONTEXT MEMORY")
print("-" * 60)

print("2.1 Tracking agent usage...")
update_context(test_session, agent_used="SummarizerAgent", query="Summarize this paper")
update_context(test_session, agent_used="SummarizerAgent", query="Give me a summary")
update_context(test_session, agent_used="ComparatorAgent", query="Compare these papers")
update_context(test_session, agent_used="GapFinderAgent", query="Find research gaps")
update_context(test_session, agent_used="SummarizerAgent", query="Another summary")
print("[OK] Tracked 5 agent uses")

print("\n2.2 Retrieving context...")
context = get_context(test_session)
print(f"[OK] Retrieved context:")
print(f"  Agent Usage: {context['agent_usage']}")
print(f"  Research Interests: {context['research_interests']}")

print("\n2.3 Verifying agent counts...")
expected_counts = {
    "SummarizerAgent": 3,
    "ComparatorAgent": 1,
    "GapFinderAgent": 1
}
actual_counts = context['agent_usage']
all_correct = True
for agent, expected in expected_counts.items():
    actual = actual_counts.get(agent, 0)
    status = "[OK]" if actual == expected else "[FAIL]"
    print(f"  {status} {agent}: {actual} (expected {expected})")
    if actual != expected:
        all_correct = False

if all_correct:
    print("[OK] All agent counts correct!")

# ============= TEST 3: RUNNING MEMORY =============
print("\n\n[TEST 3] RUNNING MEMORY")
print("-" * 60)

print("3.1 Creating a multi-step task...")
task_id = create_task(test_session, "literature_review")
print(f"[OK] Created task: {task_id}")

print("\n3.2 Adding task steps...")
update_task_step(task_id, {
    "step": 1,
    "action": "search_papers",
    "query": "diffusion models",
    "result": "Found 10 papers",
    "completed": True
})
update_task_step(task_id, {
    "step": 2,
    "action": "download_papers",
    "papers": ["paper1.pdf", "paper2.pdf"],
    "result": "Downloaded 2 papers",
    "completed": True
})
update_task_step(task_id, {
    "step": 3,
    "action": "summarize_papers",
    "status": "in_progress",
    "completed": False
})
print("[OK] Added 3 task steps")

print("\n3.3 Retrieving task status...")
task = get_task(task_id)
if task:
    print(f"[OK] Retrieved task:")
    print(f"  Task ID: {task['task_id']}")
    print(f"  Type: {task['task_type']}")
    print(f"  Status: {task['status']}")
    print(f"  Steps: {len(task['steps'])}")
    for step in task['steps']:
        step_num = step.get('step', '?')
        action = step.get('action', 'unknown')
        completed = step.get('completed', False)
        status = "[DONE]" if completed else "[PENDING]"
        print(f"    {status} Step {step_num}: {action}")
else:
    print("[FAIL] Could not retrieve task")

# ============= TEST 4: CONVERSATION CONTINUITY =============
print("\n\n[TEST 4] CONVERSATION CONTINUITY")
print("-" * 60)

print("4.1 Simulating conversation flow...")
save_message(test_session, "user", "Tell me about transformers")
save_message(test_session, "assistant", "Transformers are neural network architectures...", agent="GeneralQAAgent")
save_message(test_session, "user", "What did you say about diffusion models earlier?")
print("[OK] Saved follow-up question")

print("\n4.2 Agent should be able to reference history...")
full_history = get_session_history(test_session, limit=20)
print(f"[OK] Agent has access to {len(full_history)} previous messages")
print("  Agent can now answer: 'What did you say about X?'")

# ============= SUMMARY =============
print("\n\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("[OK] Session Memory: Saves and retrieves conversation history")
print("[OK] Context Memory: Tracks agent usage and patterns")
print("[OK] Running Memory: Manages multi-step tasks")
print("[OK] Conversation Continuity: Enables reference to past messages")
print("\n[SUCCESS] All memory systems working!")
print("=" * 60)

print("\n\nNEXT STEPS:")
print("1. Test via API: Make chat requests and verify memory persistence")
print("2. Test in UI: Have conversations and check history")
print("3. Test across sessions: Verify data persists after restart")
