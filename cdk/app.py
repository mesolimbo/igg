#!/usr/bin/env python3

import aws_cdk as cdk

from stacks.mcp_stack import McpStack
from stacks.static_site_stack import StaticSiteStack

app = cdk.App()

# Get environment configuration
env = cdk.Environment(
    account=app.node.try_get_context('account'),
    region=app.node.try_get_context('region') or 'us-east-2'
)

# Create MCP Server Stack
mcp_stack = McpStack(
    app, "IggMcpStack",
    env=env,
    description="MCP (Model Context Protocol) server infrastructure"
)

# Create Static Site Stack  
static_site_stack = StaticSiteStack(
    app, "IggStaticSiteStack", 
    env=env,
    description="Static site infrastructure"
)

app.synth()
