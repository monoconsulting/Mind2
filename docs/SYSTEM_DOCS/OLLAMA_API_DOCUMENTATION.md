# GPT-OSS:20B API Documentation for AI Developers

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Endpoints](#api-endpoints)
4. [Configuration Options](#configuration-options)
5. [Advanced Features](#advanced-features)
6. [Code Examples](#code-examples)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)

## Overview

### System Architecture
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client App    │────▶│  Ollama API  │────▶│  GPT-OSS:20B   │
│                 │     │  Port: 11435 │     │   (GPU/CUDA)    │
└─────────────────┘     └──────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │  Open WebUI  │
                        │  Port: 4000  │
                        └──────────────┘
```

### Key Specifications
- **Model**: GPT-OSS:20B (OpenAI, August 2025)
- **Size**: 13GB (quantized)
- **GPU**: NVIDIA RTX 3090 (24GB VRAM)
- **Response Time**: 1-4 seconds (GPU accelerated)
- **Context Window**: 128K tokens
- **Special Feature**: Chain-of-thought reasoning with `thinking` field

## Quick Start

### Basic API Call
```bash
curl -X POST http://127.0.0.1:11435/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss:20b",
    "prompt": "Explain quantum computing in simple terms",
    "stream": false
  }'
```

### Python Quick Start
```python
import requests
import sys
import io

# IMPORTANT: Fix encoding for Swedish characters on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

response = requests.post(
    "http://127.0.0.1:11435/api/generate",
    json={
        "model": "gpt-oss:20b",
        "prompt": "Write a Python function to sort a list",
        "stream": False
    }
)

result = response.json()
print(result["response"])
print(f"Thinking: {result.get('thinking', '')}")
```

## API Endpoints

### 1. Generate Completion
**Endpoint**: `POST /api/generate`

Generate text completion for a given prompt.

```json
{
  "model": "gpt-oss:20b",
  "prompt": "Your prompt here",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "num_predict": 512,
    "stop": ["\n", "###"],
    "seed": 42
  }
}
```

**Response**:
```json
{
  "model": "gpt-oss:20b",
  "created_at": "2025-08-18T05:20:57.838491271Z",
  "response": "Generated text here",
  "thinking": "Internal reasoning process",
  "done": true,
  "context": [/* token array */],
  "total_duration": 2083153533,
  "load_duration": 199946827,
  "prompt_eval_count": 82,
  "prompt_eval_duration": 442637750,
  "eval_count": 76,
  "eval_duration": 1438383141
}
```

### 2. Chat Completion
**Endpoint**: `POST /api/chat`

For conversational interactions with message history.

```json
{
  "model": "gpt-oss:20b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help you?"},
    {"role": "user", "content": "What's the weather like?"}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7
  }
}
```

### 3. Embeddings
**Endpoint**: `POST /api/embeddings`

Generate embeddings for text.

```json
{
  "model": "gpt-oss:20b",
  "prompt": "Text to embed"
}
```

### 4. Model Management

#### List Models
**Endpoint**: `GET /api/tags`

```bash
curl http://127.0.0.1:11435/api/tags
```

#### Pull Model
**Endpoint**: `POST /api/pull`

```json
{
  "name": "gpt-oss:20b"
}
```

#### Delete Model
**Endpoint**: `DELETE /api/delete`

```json
{
  "name": "model_name"
}
```

#### Copy Model
**Endpoint**: `POST /api/copy`

```json
{
  "source": "gpt-oss:20b",
  "destination": "my-custom-model"
}
```

### 5. Show Model Information
**Endpoint**: `POST /api/show`

```json
{
  "name": "gpt-oss:20b"
}
```

## Configuration Options

### Generation Parameters

| Parameter | Type | Default | Description | Range |
|-----------|------|---------|-------------|-------|
| `temperature` | float | 0.8 | Controls randomness | 0.0 - 2.0 |
| `top_p` | float | 0.9 | Nucleus sampling | 0.0 - 1.0 |
| `top_k` | int | 40 | Top-k sampling | 1 - 100 |
| `repeat_penalty` | float | 1.1 | Penalize repetition | 0.0 - 2.0 |
| `seed` | int | -1 | Random seed (-1 = random) | -1 or positive |
| `num_predict` | int | 512 | Max tokens to generate | 1 - 4096 |
| `num_ctx` | int | 2048 | Context window size | 512 - 128000 |
| `stop` | array | [] | Stop sequences | Array of strings |
| `tfs_z` | float | 1.0 | Tail free sampling | 0.0 - 1.0 |
| `typical_p` | float | 1.0 | Typical sampling | 0.0 - 1.0 |
| `presence_penalty` | float | 0.0 | Presence penalty | -2.0 - 2.0 |
| `frequency_penalty` | float | 0.0 | Frequency penalty | -2.0 - 2.0 |
| `mirostat` | int | 0 | Mirostat sampling (0/1/2) | 0, 1, 2 |
| `mirostat_tau` | float | 5.0 | Mirostat target entropy | 0.0 - 10.0 |
| `mirostat_eta` | float | 0.1 | Mirostat learning rate | 0.0 - 1.0 |

### System Configuration

```json
{
  "options": {
    "num_gpu": 1,          // Number of GPUs to use
    "gpu_layers": 35,      // Number of layers to offload to GPU
    "main_gpu": 0,         // Main GPU index
    "low_vram": false,     // Low VRAM mode
    "f16_kv": true,        // Use f16 for key/value cache
    "vocab_only": false,   // Load vocabulary only
    "use_mmap": true,      // Use memory mapping
    "use_mlock": false     // Lock model in memory
  }
}
```

## Advanced Features

### 1. Streaming Responses

Enable real-time token streaming for better UX:

```python
import requests
import json

def stream_response(prompt):
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "stream": True
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line)
            if not chunk.get("done"):
                print(chunk.get("response", ""), end="", flush=True)
            else:
                print("\n\nThinking:", chunk.get("thinking", ""))
                break

stream_response("Write a haiku about programming")
```

### 2. Context Preservation

Maintain conversation context across multiple requests:

```python
class ConversationManager:
    def __init__(self, model="gpt-oss:20b"):
        self.model = model
        self.context = []
        
    def chat(self, prompt):
        response = requests.post(
            "http://127.0.0.1:11435/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "context": self.context,
                "stream": False
            }
        )
        
        result = response.json()
        self.context = result.get("context", [])
        return result["response"]

# Usage
conversation = ConversationManager()
print(conversation.chat("My name is Alice"))
print(conversation.chat("What is my name?"))  # Will remember "Alice"
```

### 3. Function Calling

Implement function calling with structured outputs:

```python
import json

def function_call_prompt(description, parameters):
    prompt = f"""You are a function calling AI. 
    
Function: {description}
Parameters: {json.dumps(parameters)}

Generate a JSON response with the function call:
"""
    
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "options": {
                "temperature": 0.1,  # Low temperature for structured output
                "format": "json"
            }
        }
    )
    
    return response.json()["response"]

# Example
result = function_call_prompt(
    "search_weather",
    {"location": "Stockholm", "unit": "celsius"}
)
```

### 4. Chain-of-Thought Reasoning

Access the model's thinking process:

```python
def analyze_with_reasoning(prompt):
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": f"Think step by step: {prompt}",
            "stream": False
        }
    )
    
    result = response.json()
    return {
        "answer": result["response"],
        "reasoning": result.get("thinking", ""),
        "confidence": analyze_confidence(result["thinking"])
    }

def analyze_confidence(thinking):
    # Simple confidence analysis based on thinking clarity
    if "certain" in thinking.lower() or "clear" in thinking.lower():
        return "high"
    elif "maybe" in thinking.lower() or "possibly" in thinking.lower():
        return "medium"
    return "normal"
```

### 5. Batch Processing

Process multiple prompts efficiently:

```python
import asyncio
import aiohttp

async def batch_generate(prompts):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for prompt in prompts:
            task = session.post(
                "http://127.0.0.1:11435/api/generate",
                json={
                    "model": "gpt-oss:20b",
                    "prompt": prompt,
                    "stream": False
                }
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        results = []
        for response in responses:
            data = await response.json()
            results.append(data["response"])
        
        return results

# Usage
prompts = [
    "What is AI?",
    "Explain quantum computing",
    "Write a Python hello world"
]

results = asyncio.run(batch_generate(prompts))
```

## Code Examples

### Important: Swedish Character Encoding

Before using any Python code with Swedish characters, ensure proper encoding:

```python
import sys
import io

# Fix encoding for Swedish characters (åäö) on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
# Alternative method for console applications
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
```

### Environment Setup for Swedish Support

```python
import os
import locale

# Set UTF-8 encoding for the environment
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Set locale for Swedish
try:
    locale.setlocale(locale.LC_ALL, 'sv_SE.UTF-8')
except locale.Error:
    # Fallback for Windows
    try:
        locale.setlocale(locale.LC_ALL, 'Swedish_Sweden.1252')
    except locale.Error:
        pass  # Use default locale
```

### 1. Code Generation with Language Detection

```python
import requests
import sys
import io

# Essential encoding fix for Swedish characters
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_code(description, language=None):
    if language:
        prompt = f"Write {language} code: {description}. Only code, no explanation."
    else:
        prompt = f"Write code for: {description}. Include language comment."
    
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "options": {
                "temperature": 0.3,  # Lower for code generation
                "stop": ["```\n", "\n\n\n"]
            }
        }
    )
    
    return response.json()["response"]

# Examples
print(generate_code("fibonacci function", "Python"))
print(generate_code("REST API endpoint", "JavaScript"))
print(generate_code("sort array of integers", "C++"))
```

### 2. Multi-Language Support

```python
import requests
import sys
import io

# CRITICAL: Enable UTF-8 for Swedish characters
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def translate_and_respond(text, target_language):
    prompt = f"""Translate to {target_language} and respond appropriately:
    
Text: {text}

Response in {target_language}:"""
    
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "options": {"temperature": 0.5}
        }
    )
    
    return response.json()["response"]

# Examples
print(translate_and_respond("Hello, how are you?", "Swedish"))
print(translate_and_respond("What is the weather?", "Spanish"))
```

### 3. RAG (Retrieval Augmented Generation)

```python
def rag_query(question, context_documents):
    context = "\n\n".join([f"Document {i+1}: {doc}" 
                          for i, doc in enumerate(context_documents)])
    
    prompt = f"""Based on the following documents, answer the question.

Context:
{context}

Question: {question}

Answer based only on the provided context:"""
    
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "options": {
                "temperature": 0.2,
                "num_predict": 256
            }
        }
    )
    
    return response.json()["response"]
```

### 4. Structured Data Extraction

```python
def extract_structured_data(text, schema):
    prompt = f"""Extract data from the text according to the schema.

Text: {text}

Schema: {json.dumps(schema, indent=2)}

Return valid JSON matching the schema:"""
    
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "options": {
                "temperature": 0.1,
                "format": "json"
            }
        }
    )
    
    try:
        return json.loads(response.json()["response"])
    except:
        return {"error": "Failed to parse JSON"}

# Example
schema = {
    "name": "string",
    "age": "number",
    "email": "string"
}

text = "John Doe is 30 years old and his email is john@example.com"
data = extract_structured_data(text, schema)
```

### 5. Custom Agents

```python
class CodeReviewAgent:
    def __init__(self):
        self.model = "gpt-oss:20b"
        self.api_url = "http://127.0.0.1:11435/api/generate"
    
    def review_code(self, code, language="Python"):
        prompt = f"""Review this {language} code for:
1. Bugs and errors
2. Performance issues
3. Security vulnerabilities
4. Code style and best practices

Code:
```{language.lower()}
{code}
```

Provide a detailed review with severity levels (Critical/High/Medium/Low):"""
        
        response = requests.post(
            self.api_url,
            json={
                "model": self.model,
                "prompt": prompt,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 1024
                }
            }
        )
        
        return self._parse_review(response.json()["response"])
    
    def _parse_review(self, review_text):
        return {
            "review": review_text,
            "has_critical": "critical" in review_text.lower(),
            "has_security_issues": "security" in review_text.lower() or 
                                   "vulnerability" in review_text.lower()
        }

# Usage
agent = CodeReviewAgent()
code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
"""
review = agent.review_code(code)
print(review["review"])
```

## Performance Optimization

### 1. GPU Memory Management

```python
def check_gpu_status():
    """Check GPU memory usage and availability"""
    import subprocess
    
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        used, total = result.stdout.strip().split(", ")
        return {
            "used": used,
            "total": total,
            "available": f"{int(total.split()[0]) - int(used.split()[0])} MiB"
        }
    return None
```

### 2. Response Caching

```python
from functools import lru_cache
import hashlib

class CachedModel:
    def __init__(self, cache_size=100):
        self.cache = {}
        self.cache_size = cache_size
    
    def _hash_prompt(self, prompt, options):
        key = f"{prompt}_{json.dumps(options, sort_keys=True)}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def generate(self, prompt, options=None, use_cache=True):
        if options is None:
            options = {}
        
        cache_key = self._hash_prompt(prompt, options)
        
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        response = requests.post(
            "http://127.0.0.1:11435/api/generate",
            json={
                "model": "gpt-oss:20b",
                "prompt": prompt,
                "stream": False,
                "options": options
            }
        )
        
        result = response.json()
        
        if use_cache and len(self.cache) < self.cache_size:
            self.cache[cache_key] = result
        
        return result
```

### 3. Load Balancing Multiple Instances

```python
class LoadBalancer:
    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.current = 0
    
    def get_next_endpoint(self):
        endpoint = self.endpoints[self.current]
        self.current = (self.current + 1) % len(self.endpoints)
        return endpoint
    
    def generate(self, prompt, **kwargs):
        endpoint = self.get_next_endpoint()
        return requests.post(
            f"{endpoint}/api/generate",
            json={
                "model": "gpt-oss:20b",
                "prompt": prompt,
                **kwargs
            }
        )

# Usage with multiple Ollama instances
balancer = LoadBalancer([
    "http://127.0.0.1:11435",
    "http://127.0.0.1:11436",
    "http://127.0.0.1:11437"
])
```

### 4. Timeout and Retry Logic

```python
import time
from typing import Optional, Dict, Any

def robust_generate(
    prompt: str,
    max_retries: int = 3,
    timeout: int = 120,
    backoff_factor: float = 2.0
) -> Optional[Dict[str, Any]]:
    """Generate with automatic retry and exponential backoff"""
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://127.0.0.1:11435/api/generate",
                json={
                    "model": "gpt-oss:20b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                # Service unavailable, retry
                wait_time = backoff_factor ** attempt
                print(f"Service unavailable, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Error: {response.status_code}")
                return None
                
        except requests.Timeout:
            print(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                time.sleep(wait_time)
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    return None
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **Swedish characters broken (åäö)** | **Windows encoding** | **Add UTF-8 encoding fix (see examples above)** |
| Slow responses | Running on CPU | Ensure GPU is enabled in docker-compose |
| Out of memory | Model too large for GPU | Reduce `gpu_layers` or use smaller model |
| Connection refused | Service not running | Check `docker ps` and restart if needed |
| Timeout errors | Response too slow | Increase timeout value (120-300 seconds) |
| Empty responses | Prompt issues | Check prompt format and encoding |
| GPU not detected | Driver issues | Update NVIDIA drivers and CUDA toolkit |
| **UnicodeEncodeError** | **Windows console encoding** | **Use `io.TextIOWrapper` with UTF-8** |

### Swedish Character Testing

Test your encoding setup with this function:

```python
import requests
import sys
import io

def test_swedish_encoding():
    """Test Swedish character support"""
    
    # Essential encoding fix
    if sys.platform.startswith('win'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # Test Swedish characters
    swedish_test = "Hej! Kan du förstå åäö? Björn åker på semester till Göteborg."
    
    try:
        print("Testing Swedish characters:")
        print(f"Input: {swedish_test}")
        
        response = requests.post(
            "http://127.0.0.1:11435/api/generate",
            json={
                "model": "gpt-oss:20b",
                "prompt": f"Svara på svenska: {swedish_test}",
                "stream": False
            }
        )
        
        result = response.json()
        answer = result["response"]
        
        print(f"Output: {answer}")
        
        # Check if Swedish characters are preserved
        swedish_chars = ['å', 'ä', 'ö', 'Å', 'Ä', 'Ö']
        found_chars = [char for char in swedish_chars if char in answer]
        
        if found_chars:
            print(f"✅ Swedish characters working: {found_chars}")
            return True
        else:
            print("❌ No Swedish characters in response")
            return False
            
    except UnicodeEncodeError as e:
        print(f"❌ Encoding error: {e}")
        print("Solution: Add UTF-8 encoding fix at start of script")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Run the test
if __name__ == "__main__":
    test_swedish_encoding()
```

### Reading Swedish Files

```python
def read_swedish_file(filename):
    """Read file with Swedish characters safely"""
    try:
        # Try UTF-8 first (recommended)
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # Fallback to Windows-1252 (common on Windows)
        with open(filename, 'r', encoding='windows-1252') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def process_swedish_text_file(filename):
    """Process a Swedish text file with the model"""
    
    # Essential encoding fix
    if sys.platform.startswith('win'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    content = read_swedish_file(filename)
    if not content:
        return None
    
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": f"Sammanfatta denna svenska text: {content}",
            "stream": False
        }
    )
    
    return response.json()["response"]

# Example usage
# summary = process_swedish_text_file("svenska_test.txt")
# print(summary)
```

### Debug Logging

```python
import logging
import sys
import io

# Fix encoding for logs with Swedish characters
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ollama_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def debug_generate(prompt):
    logger.debug(f"Sending prompt: {prompt[:100]}...")
    
    start_time = time.time()
    response = requests.post(
        "http://127.0.0.1:11435/api/generate",
        json={
            "model": "gpt-oss:20b",
            "prompt": prompt,
            "stream": False
        }
    )
    
    elapsed = time.time() - start_time
    
    result = response.json()
    logger.debug(f"Response time: {elapsed:.2f}s")
    logger.debug(f"Tokens generated: {result.get('eval_count', 0)}")
    logger.debug(f"Tokens/sec: {result.get('eval_count', 0) / elapsed:.2f}")
    
    return result
```

### Health Check Endpoint

```python
def health_check():
    """Comprehensive health check for the API"""
    checks = {
        "api_available": False,
        "model_loaded": False,
        "gpu_enabled": False,
        "response_time": None
    }
    
    try:
        # Check API availability
        response = requests.get("http://127.0.0.1:11435/api/tags", timeout=5)
        checks["api_available"] = response.status_code == 200
        
        # Check if model is loaded
        if checks["api_available"]:
            models = response.json().get("models", [])
            checks["model_loaded"] = any(m["name"] == "gpt-oss:20b" for m in models)
        
        # Test generation
        if checks["model_loaded"]:
            start = time.time()
            test_response = requests.post(
                "http://127.0.0.1:11435/api/generate",
                json={
                    "model": "gpt-oss:20b",
                    "prompt": "Hi",
                    "stream": False,
                    "options": {"num_predict": 1}
                },
                timeout=30
            )
            checks["response_time"] = time.time() - start
            
            # Check if GPU is being used (response time < 5s for simple prompt)
            checks["gpu_enabled"] = checks["response_time"] < 5
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    return checks

# Usage
status = health_check()
print(json.dumps(status, indent=2))
```

## Best Practices

1. **🇸🇪 ALWAYS fix encoding for Swedish characters** - Add UTF-8 encoding at start of every script
2. **Always set appropriate timeouts** - GPT-OSS:20B can take 30-120 seconds for complex prompts
3. **Use streaming for better UX** - Stream tokens as they're generated
4. **Implement retry logic** - Handle transient failures gracefully
5. **Cache frequent queries** - Reduce load and improve response times
6. **Monitor GPU memory** - Ensure sufficient VRAM is available
7. **Use appropriate temperatures** - Lower for factual, higher for creative tasks
8. **Batch similar requests** - Process multiple prompts efficiently
9. **Implement rate limiting** - Prevent overload in production
10. **Log thinking process** - Useful for debugging and understanding responses
11. **Validate JSON outputs** - Always parse and validate structured responses
12. **Test with Swedish characters** - Use the test function to verify encoding works

### Essential Encoding Template

Always start your Python scripts with this template when using Swedish:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
import requests

# CRITICAL: Fix encoding for Swedish characters on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Your code here...
def main():
    # Test Swedish characters first
    print("Testing: åäö ÅÄÖ")
    
    # Your API calls here
    pass

if __name__ == "__main__":
    main()
```

## Additional Resources

- **Ollama Documentation**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **OpenAI GPT-OSS Paper**: https://openai.com/research/gpt-oss
- **Open WebUI**: http://127.0.0.1:4000
- **Model Card**: Available via `/api/show` endpoint

## Support

For issues or questions:
1. Check container logs: `docker compose logs ollama`
2. Verify GPU status: `nvidia-smi`
3. Test API health: Use the health check function above
4. Monitor resource usage: `docker stats`

---

*Last updated: August 2025*
*Model version: GPT-OSS:20B (August 2025 release)*
*API version: Ollama v0.11.4*