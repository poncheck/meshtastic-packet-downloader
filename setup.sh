#!/bin/bash
# Meshtastic Packet Downloader - Setup Script

set -e  # Exit on error

echo "=========================================="
echo "Meshtastic Packet Downloader - Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓${NC} Found Python $PYTHON_VERSION"

# Check if venv module is available
if ! python3 -m venv --help &> /dev/null; then
    echo -e "${RED}Error: python3-venv is not installed${NC}"
    echo "Please run: sudo apt install python3-venv python3-full"
    exit 1
fi

echo -e "${GREEN}✓${NC} python3-venv is available"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Warning: venv directory already exists${NC}"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✓${NC} Virtual environment recreated"
    else
        echo "Using existing virtual environment"
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓${NC} pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
if pip install -r requirements.txt; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}Error: Failed to install dependencies${NC}"
    exit 1
fi

# Create config file if it doesn't exist
echo ""
if [ ! -f "config.yaml" ]; then
    echo "Creating config.yaml from example..."
    cp config.example.yaml config.yaml
    echo -e "${GREEN}✓${NC} config.yaml created"
    echo -e "${YELLOW}⚠${NC}  Please edit config.yaml and configure your MQTT broker settings!"
else
    echo -e "${YELLOW}⚠${NC}  config.yaml already exists, skipping..."
fi

# Create run script
echo ""
echo "Creating run.sh helper script..."
cat > run.sh << 'EOF'
#!/bin/bash
# Quick run script - activates venv and runs the downloader

cd "$(dirname "$0")"
source venv/bin/activate
python meshtastic_downloader.py "$@"
EOF
chmod +x run.sh
echo -e "${GREEN}✓${NC} run.sh created"

echo ""
echo "=========================================="
echo -e "${GREEN}Setup completed successfully!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config.yaml to configure your MQTT broker:"
echo "   nano config.yaml"
echo ""
echo "2. Run the downloader:"
echo "   ./run.sh"
echo ""
echo "   Or manually:"
echo "   source venv/bin/activate"
echo "   python meshtastic_downloader.py"
echo ""
