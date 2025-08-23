import json
import asyncio
from typing import Any, Dict, List

import mcp_markov_models


def create_response(status_code: int, body: dict, headers: dict = None):
    """Create a standardized API Gateway response."""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body)
    }


async def handle_mcp_request(body: dict):
    """Handle MCP protocol requests."""
    try:
        method = body.get('method')
        params = body.get('params', {})
        
        if method == 'initialize':
            # MCP initialization handshake
            return {
                "jsonrpc": "2.0",
                "id": body.get('id'),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "logging": {},
                        "prompts": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "IGG MCP Server",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == 'notifications/initialized':
            # Acknowledge initialization complete - notification has no response
            if body.get('id') is None:
                # This is a notification, no response needed
                return None
            return {
                "jsonrpc": "2.0",
                "id": body.get('id'),
                "result": {}
            }
        
        elif method == 'ping':
            # Health check ping
            return {
                "jsonrpc": "2.0",
                "id": body.get('id'),
                "result": {
                    "status": "ok"
                }
            }
        
        elif method == 'tools/list':
            # List available tools
            tools = [
                {
                    "name": "list_models",
                    "description": "List available Markov models for text generation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "generate_ideas",
                    "description": "Generate creative text ideas using a Markov model",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "model_name": {
                                "type": "string",
                                "description": "Name of the model to use for generation"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of ideas to generate",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["model_name"]
                    }
                },
                {
                    "name": "generate_with_template",
                    "description": "Generate ideas using a template with placeholders ($1, $2, etc.)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "model_name": {
                                "type": "string",
                                "description": "Name of the model to use for generation"
                            },
                            "template": {
                                "type": "string",
                                "description": "Template string with placeholders like 'A $1 for $2 people'"
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of ideas to generate",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 50
                            }
                        },
                        "required": ["model_name", "template"]
                    }
                }
            ]
            
            return {
                "jsonrpc": "2.0",
                "id": body.get('id'),
                "result": {"tools": tools}
            }
        
        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            if tool_name == 'list_models':
                models = await mcp_markov_models.list_models()
                result = {"content": [{"type": "text", "text": json.dumps(models, indent=2)}]}
                
            elif tool_name == 'generate_ideas':
                model_name = arguments["model_name"]
                count = arguments.get("count", 5)
                
                ideas = await mcp_markov_models.generate_ideas(model_name, count)
                
                response_data = {
                    "model": model_name,
                    "count": count,
                    "ideas": ideas
                }
                
                result = {"content": [{"type": "text", "text": json.dumps(response_data, indent=2)}]}
                
            elif tool_name == 'generate_with_template':
                model_name = arguments["model_name"]
                template = arguments["template"]
                count = arguments.get("count", 5)
                
                ideas = await mcp_markov_models.generate_with_template(model_name, template, count)
                
                response_data = {
                    "model": model_name,
                    "template": template,
                    "count": count,
                    "ideas": ideas
                }
                
                result = {"content": [{"type": "text", "text": json.dumps(response_data, indent=2)}]}
                
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": body.get('id'),
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }
            
            return {
                "jsonrpc": "2.0",
                "id": body.get('id'),
                "result": result
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": body.get('id'),
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }
            
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body.get('id'),
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
        }


def lambda_handler(event, context):
    """Main Lambda handler for API Gateway events."""
    
    # Handle preflight CORS requests
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    # Handle GET request - return basic info (auth handled by API Gateway)
    if event.get('httpMethod') == 'GET':
        return create_response(200, {
            "service": "IGG MCP Server",
            "description": "Markov chain text generation tools for creative idea generation",
            "version": "1.0.0"
        })
    
    # Parse request body for POST requests (auth already validated by API Gateway)
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return create_response(400, {"error": "Invalid JSON in request body"})
    
    # Handle MCP requests asynchronously
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handle_mcp_request(body))
            if result is None:
                # This was a notification with no response
                return create_response(200, {})
            return create_response(200, result)
        finally:
            loop.close()
    except Exception as e:
        return create_response(500, {"error": f"Internal server error: {str(e)}"})
