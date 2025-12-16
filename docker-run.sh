#!/bin/bash

set -e
set -x

echo "=== Launching CaseK2NeuroTechDevelopmentAssistant project via Docker ==="
echo "Current directory: $(pwd)"
echo

# Check for .env files in all directories and create from .env.copy if needed
echo "Checking for .env files in all project directories..."
find . -type f -name ".env.copy" | while read copy_file; do
    dir=$(dirname "$copy_file")
    env_file="$dir/.env"
    
    if [ -f "$copy_file" ]; then
        if [ ! -f "$env_file" ]; then
            echo "Creating .env from .env.copy in: $dir"
            cp "$copy_file" "$env_file"
            echo "Created: $env_file"
        else
            echo ".env already exists in: $dir"
        fi
    fi
done

echo "Environment file setup completed."
echo

# Check for docker-compose availability
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed!"
    echo "Please install Docker and Docker Compose"
    exit 1
fi

# Check for necessary files
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found!"
    exit 1
fi

# Launch parameters
ACTION=${1:-up}
FORCE_REBUILD=${2:-false}

case $ACTION in
    "up")
        if [ "$FORCE_REBUILD" = "true" ]; then
            echo "Building and launching containers..."
            docker-compose up -d --build
        else
            echo "Launching containers..."
            docker-compose up -d
        fi
        ;;
    "down")
        echo "Stopping containers..."
        docker-compose down
        ;;
    "build")
        echo "Building containers..."
        docker-compose build
        ;;
    "logs")
        echo "Viewing logs..."
        docker-compose logs -f
        ;;
    "restart")
        echo "Restarting containers..."
        docker-compose restart
        ;;
    "clean")
        echo "Cleaning up..."
        docker-compose down -v
        ;;
    "check")
        echo "=== Container status ==="
        docker-compose ps
        echo -e "\n=== Service verification ==="
        
        # Backend check
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|404"; then
            echo "Backend available at http://localhost:5000"
        else
            echo "Backend unavailable"
        fi
        
        # Frontend check
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
            echo "Frontend available at http://localhost:3000"
        else
            echo "Frontend unavailable"
        fi
        ;;
    *)
        echo "Usage: $0 [up|down|build|logs|restart|clean|check] [true for rebuild]"
        echo "Examples:"
        echo "  $0 up          # Launch containers"
        echo "  $0 up true     # Rebuild and launch"
        echo "  $0 check       # Check status"
        exit 1
        ;;
esac