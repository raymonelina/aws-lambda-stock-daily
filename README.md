# AWS Lambda Stock Daily

This project contains an AWS Lambda function for fetching daily stock data.

## Running Tests

To run the unit tests, first ensure you have the project dependencies installed by synchronizing your virtual environment:

```bash
uv sync
```

Then, run pytest from the root directory:

```bash
uv run pytest
```

## Building Docker Image

To build the Docker image, run the `build_docker_image.sh` script:

```bash
./build_docker_image.sh
```
