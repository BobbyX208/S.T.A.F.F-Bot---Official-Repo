#!/usr/bin/env python3
"""
Cross-platform setup script for Discord Staff Bot
Works on Windows, macOS, and Linux without requiring bash
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m' if platform.system() != 'Windows' else ''
    YELLOW = '\033[93m' if platform.system() != 'Windows' else ''
    RED = '\033[91m' if platform.system() != 'Windows' else ''
    BLUE = '\033[94m' if platform.system() != 'Windows' else ''
    NC = '\033[0m' if platform.system() != 'Windows' else ''

def print_color(text, color):
    """Print colored text"""
    if platform.system() == 'Windows':
        # Windows doesn't support ANSI colors by default
        print(text)
    else:
        print(f"{color}{text}{Colors.NC}")

def run_command(cmd, check=True):
    """Run a shell command"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_python_version():
    """Check if Python version is 3.10+"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print_color(f"✓ Python {version.major}.{version.minor}.{version.micro} detected", Colors.GREEN)
        return True
    else:
        print_color(f"✗ Python 3.10+ required, found {version.major}.{version.minor}", Colors.RED)
        return False

def create_virtualenv():
    """Create virtual environment"""
    print_color("\nCreating virtual environment...", Colors.YELLOW)
    
    if os.path.exists('venv'):
        print_color("✓ Virtual environment already exists", Colors.GREEN)
        return True
    
    try:
        import venv
        venv.create('venv', with_pip=True)
        print_color("✓ Virtual environment created", Colors.GREEN)
        return True
    except Exception as e:
        print_color(f"✗ Failed to create virtual environment: {e}", Colors.RED)
        return False

def install_requirements():
    """Install Python requirements"""
    print_color("\nInstalling requirements...", Colors.YELLOW)
    
    # Determine pip path
    if platform.system() == 'Windows':
        pip_path = os.path.join('venv', 'Scripts', 'pip')
    else:
        pip_path = os.path.join('venv', 'bin', 'pip')
    
    if os.path.exists(pip_path):
        # Use virtual env pip
        success, output = run_command(f'"{pip_path}" install -r requirements.txt')
    else:
        # Fallback to system pip
        success, output = run_command(f'{sys.executable} -m pip install -r requirements.txt')
    
    if success:
        print_color("✓ Requirements installed", Colors.GREEN)
    else:
        print_color(f"✗ Failed to install requirements: {output}", Colors.RED)
    
    return success

def create_directories():
    """Create necessary directories"""
    print_color("\nCreating project directories...", Colors.YELLOW)
    
    dirs = ['logs', 'cogs', 'utils', 'data']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print_color(f"  Created {dir_name}/", Colors.GREEN)
    
    # Create __init__.py files
    Path('cogs/__init__.py').touch()
    Path('utils/__init__.py').touch()
    
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    print_color("\nChecking environment configuration...", Colors.YELLOW)
    
    if not Path('.env').exists():
        if Path('.env.example').exists():
            shutil.copy('.env.example', '.env')
            print_color("✓ Created .env from .env.example", Colors.GREEN)
        else:
            # Create basic .env
            with open('.env', 'w') as f:
                f.write("""# Discord Configuration
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
""")
            print_color("✓ Created basic .env file", Colors.GREEN)
        
        print_color("⚠ IMPORTANT: Edit .env with your actual configuration!", Colors.RED)
    else:
        print_color("✓ .env file exists", Colors.GREEN)

def create_config_file():
    """Create config.json if it doesn't exist"""
    print_color("\nChecking configuration file...", Colors.YELLOW)
    
    if not Path('config.json').exists():
        if Path('config.json.example').exists():
            shutil.copy('config.json.example', 'config.json')
            print_color("✓ Created config.json from config.json.example", Colors.GREEN)
        else:
            # Create basic config
            with open('config.json', 'w') as f:
                f.write("""{
    "bot": {
        "name": "StaffBot",
        "version": "1.0.0",
        "status": "online",
        "activity": "Watching for updates"
    },
    "colors": {
        "primary": 5865F2,
        "success": 57F287,
        "warning": "FEE75C",
        "error": "ED4245"
    },
    "git": {
        "auto_reload": true,
        "reload_command": "reload",
        "allowed_roles": ["Admin", "Moderator"]
    }
}""")
            print_color("✓ Created basic config.json", Colors.GREEN)
    else:
        print_color("✓ config.json exists", Colors.GREEN)

def print_next_steps():
    """Print next steps instructions"""
    print_color("\n" + "="*40, Colors.BLUE)
    print_color("Setup Complete!", Colors.GREEN)
    print_color("="*40, Colors.BLUE)
    
    print_color("\nNext Steps:", Colors.YELLOW)
    print_color("1. Edit .env with your Discord bot token and configuration", Colors.NC)
    print_color("2. Review and edit config.json if needed", Colors.NC)
    
    print_color("\nTo run the bot:", Colors.YELLOW)
    if platform.system() == 'Windows':
        print_color("  venv\\Scripts\\activate && python main.py", Colors.GREEN)
    else:
        print_color("  source venv/bin/activate && python main.py", Colors.GREEN)
    
    print_color("\nUseful Commands (in Discord):", Colors.YELLOW)
    print_color("  !reload    - Reload all cogs", Colors.NC)
    print_color("  !gitpull   - Manual git pull", Colors.NC)
    print_color("  !gitstatus - Check git status", Colors.NC)
    
    print_color("\nHappy coding! 🚀\n", Colors.GREEN)

def main():
    """Main setup function"""
    print_color("="*40, Colors.BLUE)
    print_color("Discord Staff Bot Setup", Colors.GREEN)
    print_color("="*40, Colors.BLUE)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtualenv():
        response = input("Continue without virtual environment? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        print_color("Failed to install requirements", Colors.RED)
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create configuration files
    create_env_file()
    create_config_file()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()