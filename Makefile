.PHONY: build layer synth deploy clean test help

# Default target
help:
	@echo "Available targets:"
	@echo "  build   - Build all artifacts (layer + synth)"
	@echo "  layer   - Build Lambda layer with dependencies"
	@echo "  synth   - Synthesize CDK CloudFormation templates"
	@echo "  deploy  - Deploy to AWS (depends on build)"
	@echo "  clean   - Remove build artifacts"
	@echo "  test    - Run tests"

# Build Lambda layer using Docker (Linux environment)
layer:
	@echo "Building Lambda layer with Docker..."
	rm -rf lambda-layer/python
	mkdir -p lambda-layer/python
	docker run --rm --entrypoint pip -v "$(CURDIR)/lambda-layer:/layer" public.ecr.aws/lambda/python:3.12 \
		install pandas nltk numpy python-dateutil pytz regex click joblib tqdm \
		-t /layer/python --no-cache-dir
	@echo "Layer built successfully"

# Synthesize CDK templates
synth: layer
	cd cdk && pipenv run npx cdk synth

# Build all artifacts
build: layer synth

# Deploy to AWS (depends on build)
deploy: build
	cd cdk && pipenv run npx cdk deploy --all --require-approval never

# Clean build artifacts
clean:
	rm -rf lambda-layer/python
	rm -rf cdk/cdk.out

# Run tests
test:
	pipenv run pytest test/ -v
