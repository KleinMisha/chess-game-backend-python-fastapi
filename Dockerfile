
## ------------ STAGE 1: BUILD PYTHON ENVIRONMENT USING UV --------------- ##  
FROM python:3.13-slim-bookworm AS builder 

#  Builder tools + curl 
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential && \
    curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/* 

# Install UV 
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up UV environment path to make it available globally 
ENV PATH="/root/.local/bin:$PATH"

# Directory for application / code within the container + transfer pyproject.toml into it
WORKDIR /app 
COPY ./pyproject.toml .

# Install dependencies using UV 
RUN uv sync 



## ------------ STAGE 2: PRODUCTION / RUNNING THE APPLICATION --------------- ## 
FROM python:3.13-slim-bookworm AS production

WORKDIR /app

# Copy over the source-code (NOTE: .docker-ignore lists all stuff in this repo we do not need to transfer into the container)
COPY /src src

# Copy over the environment build in the previous step
COPY --from=builder /app/.venv .venv

# Expose port for FastAPI
EXPOSE 8000

# Start the Application 
CMD [ "uvicorn", "src.main:app", "--log-level", "info", "--host" ,"0.0.0.0", "--port", "8000"]