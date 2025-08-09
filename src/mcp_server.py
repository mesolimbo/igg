#!/usr/bin/env python3
"""
MCP Server for IGG (Idea Generator Generator)
Provides Markov chain text generation tools for creative idea generation.
"""

import asyncio
import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

import mcp_markov_models


app = Server("igg-markov")


@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="list_models",
            description="List available Markov models for text generation",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="generate_ideas",
            description="Generate creative text ideas using a Markov model",
            inputSchema={
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
        ),
        Tool(
            name="generate_with_template",
            description="Generate ideas using a template with placeholders ($1, $2, etc.)",
            inputSchema={
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
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool execution requests."""
    try:
        if name == "list_models":
            models = await mcp_markov_models.list_models()
            return [TextContent(
                type="text",
                text=json.dumps(models, indent=2)
            )]
            
        elif name == "generate_ideas":
            model_name = arguments["model_name"]
            count = arguments.get("count", 5)
            
            ideas = await mcp_markov_models.generate_ideas(model_name, count)
            
            result = {
                "model": model_name,
                "count": count,
                "ideas": ideas
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        elif name == "generate_with_template":
            model_name = arguments["model_name"]
            template = arguments["template"]
            count = arguments.get("count", 5)
            
            ideas = await mcp_markov_models.generate_with_template(model_name, template, count)
            
            result = {
                "model": model_name,
                "template": template,
                "count": count,
                "ideas": ideas
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
