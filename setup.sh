#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Discord Staff Bot Setup Script${NC}"
echo -e "${BLUE}================================${NC}\n"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION detected (OK)${NC}"
            return 0
        else
            echo -e "${RED}✗ Python 3.10+ required, found $PYTHON_VERSION${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Python 3 not found${NC}"
        return 1
    fi
}

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if ! check_python; then
    echo -e "${RED}Please install Python 3.10 or higher:${NC}"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  - CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "  - macOS: brew install python@3.11"
    echo "  - Windows: Download from https://www.python.org/downloads/"
    exit 1
fi

# Check for venv module
echo -e "\n${YELLOW}Checking for Python venv module...${NC}"
if ! python3 -c "import venv" 2>/dev/null; then
    echo -e "${RED}✗ Python venv module not found${NC}"
    echo -e "${YELLOW}Installing venv module...${NC}"
    
    # Detect OS and install venv
    if command_exists apt; then
        sudo apt update
        sudo apt install -y python3-venv python3-full
    elif command_exists yum; then
        sudo yum install -y python3-virtualenv
    elif command_exists dnf; then
        sudo dnf install -y python3-virtualenv
    elif command_exists brew; then
        brew install python3
    else
        echo -e "${RED}Could not install venv automatically.${NC}"
        echo "Please install python3-venv manually:"
        echo "  - Ubuntu/Debian: sudo apt install python3-venv"
        echo "  - CentOS/RHEL: sudo yum install python3-virtualenv"
        exit 1
    fi
    
    # Verify installation
    if python3 -c "import venv" 2>/dev/null; then
        echo -e "${GREEN}✓ venv module installed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to install venv module${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ venv module found${NC}"
fi

# Check for pip
echo -e "\n${YELLOW}Checking for pip...${NC}"
if ! command_exists pip3; then
    echo -e "${YELLOW}Installing pip...${NC}"
    
    if command_exists apt; then
        sudo apt install -y python3-pip
    elif command_exists yum; then
        sudo yum install -y python3-pip
    elif command_exists dnf; then
        sudo dnf install -y python3-pip
    else
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py
        rm get-pip.py
    fi
    
    if command_exists pip3; then
        echo -e "${GREEN}✓ pip installed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to install pip${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ pip found${NC}"
fi

# Check for git
echo -e "\n${YELLOW}Checking for git...${NC}"
if ! command_exists git; then
    echo -e "${YELLOW}Installing git...${NC}"
    
    if command_exists apt; then
        sudo apt install -y git
    elif command_exists yum; then
        sudo yum install -y git
    elif command_exists dnf; then
        sudo dnf install -y git
    elif command_exists brew; then
        brew install git
    else
        echo -e "${RED}Please install git manually: https://git-scm.com/downloads${NC}"
        exit 1
    fi
    
    if command_exists git; then
        echo -e "${GREEN}✓ git installed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to install git${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ git found${NC}"
fi

# Create virtual environment (with fallback options)
echo -e "\n${YELLOW}Creating virtual environment...${NC}"

# Try different methods to create virtual environment
if python3 -m venv venv 2>/dev/null; then
    echo -e "${GREEN}✓ Virtual environment created with venv${NC}"
elif python3 -m virtualenv venv 2>/dev/null; then
    echo -e "${GREEN}✓ Virtual environment created with virtualenv${NC}"
elif command_exists virtualenv; then
    virtualenv venv
    echo -e "${GREEN}✓ Virtual environment created with virtualenv${NC}"
else
    echo -e "${RED}✗ Could not create virtual environment${NC}"
    echo -e "${YELLOW}Installing virtualenv as fallback...${NC}"
    
    pip3 install virtualenv
    
    if command_exists virtualenv; then
        virtualenv venv
        echo -e "${GREEN}✓ Virtual environment created with virtualenv${NC}"
    else
        echo -e "${RED}✗ Failed to create virtual environment${NC}"
        echo -e "${YELLOW}Installing packages globally instead...${NC}"
        
        # Install packages globally as last resort
        pip3 install -r requirements.txt
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Packages installed globally${NC}"
        else
            echo -e "${RED}✗ Failed to install packages${NC}"
            exit 1
        fi
        
        # Continue without venv
        VENV_ACTIVE=false
    fi
fi

# Activate virtual environment if created
if [ -d "venv" ]; then
    echo -e "\n${YELLOW}Activating virtual environment...${NC}"
    
    # Detect OS and use appropriate activation method
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        source venv/Scripts/activate 2>/dev/null || . venv/Scripts/activate
    else
        # Unix-like
        source venv/bin/activate 2>/dev/null || . venv/bin/activate
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
        VENV_ACTIVE=true
        
        # Upgrade pip in venv
        echo -e "\n${YELLOW}Upgrading pip...${NC}"
        pip install --upgrade pip
    else
        echo -e "${RED}✗ Failed to activate virtual environment${NC}"
        VENV_ACTIVE=false
    fi
fi

# Install requirements
echo -e "\n${YELLOW}Installing Python requirements...${NC}"

if [ "$VENV_ACTIVE" = true ]; then
    pip install -r requirements.txt
else
    pip3 install --user -r requirements.txt
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Requirements installed successfully${NC}"
else
    echo -e "${RED}✗ Failed to install requirements${NC}"
    exit 1
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating project directories...${NC}"
mkdir -p logs cogs utils data
touch cogs/__init__.py
touch utils/__init__.py

echo -e "${GREEN}✓ Directories created${NC}"

# Check if .env exists, create from example if not
echo -e "\n${YELLOW}Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
        echo -e "${RED}⚠ IMPORTANT: Edit .env with your actual configuration!${NC}"
    else
        # Create basic .env file
        cat > .env << EOF
# Discord Configuration
DISCORD_TOKEN=your_bot_token_here

# Database Configuration (postgresql, mysql, or json)
DB_TYPE=json

# GitHub Configuration (for auto-pull)
GITHUB_REPO=yourusername/your-repo
GITHUB_BRANCH=main
GITHUB_POLL_INTERVAL=60

# Bot Configuration
COMMAND_PREFIX=!
STAFF_ROLE_ID=your_staff_role_id
EOF
        echo -e "${GREEN}✓ Created basic .env file${NC}"
        echo -e "${RED}⚠ IMPORTANT: Edit .env with your actual configuration!${NC}"
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Check if config.json exists, create from example if not
if [ ! -f "config.json" ]; then
    if [ -f "config.json.example" ]; then
        cp config.json.example config.json
        echo -e "${GREEN}✓ Created config.json from config.json.example${NC}"
    else
        # Create basic config.json
        cat > config.json << EOF
{
    "bot": {
        "name": "StaffBot",
        "version": "1.0.0",
        "status": "online",
        "activity": "Watching for updates"
    },
    "colors": {
        "primary": 5865F2,
        "success": 57F287,
        "warning": FEE75C,
        "error": ED4245
    },
    "git": {
        "auto_reload": true,
        "reload_command": "reload",
        "allowed_roles": ["Admin", "Moderator"]
    }
}
EOF
        echo -e "${GREEN}✓ Created basic config.json${NC}"
    fi
else
    echo -e "${GREEN}✓ config.json exists${NC}"
fi

# Test database dependencies based on DB_TYPE
echo -e "\n${YELLOW}Checking database dependencies...${NC}"
if [ -f ".env" ]; then
    source .env
    DB_TYPE=${DB_TYPE:-json}
    
    case $DB_TYPE in
        postgresql)
            echo -e "${BLUE}PostgreSQL selected - checking asyncpg...${NC}"
            if python3 -c "import asyncpg" 2>/dev/null; then
                echo -e "${GREEN}✓ asyncpg installed${NC}"
            else
                echo -e "${YELLOW}Installing asyncpg...${NC}"
                pip install asyncpg
            fi
            ;;
        mysql)
            echo -e "${BLUE}MySQL selected - checking aiomysql...${NC}"
            if python3 -c "import aiomysql" 2>/dev/null; then
                echo -e "${GREEN}✓ aiomysql installed${NC}"
            else
                echo -e "${YELLOW}Installing aiomysql...${NC}"
                pip install aiomysql
            fi
            ;;
        *)
            echo -e "${BLUE}JSON storage selected (no database server required)${NC}"
            ;;
    esac
fi

# Create systemd service file (optional)
echo -e "\n${YELLOW}Do you want to create a systemd service file? (y/n)${NC}"
read -r CREATE_SERVICE

if [[ $CREATE_SERVICE =~ ^[Yy]$ ]]; then
    cat > discord-staff-bot.service << EOF
[Unit]
Description=Discord Staff Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    echo -e "${GREEN}✓ Created discord-staff-bot.service${NC}"
    echo -e "${YELLOW}To install systemd service:${NC}"
    echo "  sudo mv discord-staff-bot.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable discord-staff-bot"
    echo "  sudo systemctl start discord-staff-bot"
fi

# Create Docker support files (optional)
echo -e "\n${YELLOW}Do you want to create Docker files? (y/n)${NC}"
read -r CREATE_DOCKER

if [[ $CREATE_DOCKER =~ ^[Yy]$ ]]; then
    # Create Dockerfile
    cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Create necessary directories
RUN mkdir -p logs cogs utils data

# Run the bot
CMD ["python", "main.py"]
EOF

    # Create docker-compose.yml
    cat > docker-compose.yml << EOF
version: '3.8'

services:
  bot:
    build: .
    environment:
      - DISCORD_TOKEN=\${DISCORD_TOKEN}
      - DB_TYPE=\${DB_TYPE}
      - GITHUB_REPO=\${GITHUB_REPO}
      - GITHUB_BRANCH=\${GITHUB_BRANCH}
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./config.json:/app/config.json
      - ./cogs:/app/cogs
      - ./.env:/app/.env
      - ./.git:/app/.git  # Mount git for auto-pull
    restart: unless-stopped

  # Optional: Add PostgreSQL if needed
  # postgres:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: discord_bot
  #     POSTGRES_USER: postgres
  #     POSTGRES_PASSWORD: \${DB_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"
  #   restart: unless-stopped

# volumes:
#   postgres_data:
EOF

    echo -e "${GREEN}✓ Created Docker files${NC}"
    echo -e "${YELLOW}To run with Docker:${NC}"
    echo "  docker-compose up -d"
fi

# Create Windows batch file for easy setup
cat > setup.bat << 'EOF'
@echo off
echo Discord Staff Bot Setup for Windows
echo ===================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.10+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Create directories
mkdir logs 2>nul
mkdir cogs 2>nul
mkdir utils 2>nul
mkdir data 2>nul

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env with your bot token
echo 2. Run: python main.py
echo.

pause
EOF

echo -e "\n${GREEN}✓ Created Windows setup script (setup.bat)${NC}"

# Final instructions
echo -e "\n${BLUE}================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}================================${NC}\n"

echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Edit ${BLUE}.env${NC} with your Discord bot token and configuration"
echo -e "2. Review and edit ${BLUE}config.json${NC} if needed"
echo -e "3. Run the bot: ${GREEN}python main.py${NC}"

if [ "$VENV_ACTIVE" = true ]; then
    echo -e "\n${YELLOW}To activate virtual environment manually:${NC}"
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo -e "  ${BLUE}venv\\Scripts\\activate${NC}"
    else
        echo -e "  ${BLUE}source venv/bin/activate${NC}"
    fi
fi

echo -e "\n${YELLOW}Useful Commands:${NC}"
echo -e "  Start bot: ${GREEN}python main.py${NC}"
echo -e "  Reload all cogs: ${GREEN}!reload${NC} (in Discord)"
echo -e "  Manual git pull: ${GREEN}!gitpull${NC} (in Discord)"
echo -e "  Check git status: ${GREEN}!gitstatus${NC} (in Discord)"

echo -e "\n${GREEN}Happy coding! 🚀${NC}\n"