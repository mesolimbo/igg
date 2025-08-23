#!/usr/bin/env python3

import aws_cdk as cdk

from igg_stack import IggStack

app = cdk.App()
IggStack(app, "IggStack", env=cdk.Environment(
    account=app.node.try_get_context('account'),
    region=app.node.try_get_context('region') or 'us-east-2'
))

app.synth()
