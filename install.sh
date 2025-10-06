#!/bin/bash
set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main installation function
install_metaxsfr() {
    print_status "Starting METAXSFR installation..."

    # Detect platform
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)

    # Map architecture names
    case $ARCH in
        x86_64) ARCH="64" ;;
        arm64|aarch64) ARCH="arm64" ;;
        *)
            print_warning "Unknown architecture: $ARCH, defaulting to 64-bit"
            ARCH="64"
            ;;
    esac

    # Map OS names and create platform string
    case $OS in
        linux) PLATFORM="linux-${ARCH}" ;;
        darwin) PLATFORM="osx-${ARCH}" ;;
        *)
            print_error "Unsupported operating system: $OS"
            print_error "METAXSFR supports Linux and macOS only"
            exit 1
            ;;
    esac

    print_status "Detected platform: $PLATFORM"

    # Check prerequisites
    print_status "Checking prerequisites..."

    if ! command_exists git; then
        print_error "git is required but not installed."
        print_error "Please install git and try again."
        exit 1
    fi

    # Check for conda/mamba
    CONDA_CMD=""
    if command_exists mamba; then
        CONDA_CMD="mamba"
        print_status "Found mamba"
    elif command_exists conda; then
        CONDA_CMD="conda"
        print_status "Found conda"
    else
        print_error "Neither conda nor mamba found."
        print_error "Please install conda/mamba first:"
        print_error "  - Miniconda: https://docs.conda.io/en/latest/miniconda.html"
        print_error "  - Mambaforge: https://github.com/conda-forge/miniforge"
        exit 1
    fi

    # Set installation directory
    INSTALL_DIR="${HOME}/metaxsfr"
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists"
        read -p "Remove existing installation? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            print_status "Removed existing installation"
        else
            print_error "Installation cancelled"
            exit 1
        fi
    fi

    # Clone repository
    print_status "Cloning METAXSFR repository..."
    git clone https://github.com/nalarbp/metaxsfr.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Check for conda-lock file
    LOCK_FILE="conda-lock.yml"
    if [ -f "$LOCK_FILE" ]; then
        print_status "Using conda-lock file for cross-platform installation"

        # Check if conda-lock is available
        if ! command_exists conda-lock; then
            print_warning "conda-lock not found, installing it first..."
            $CONDA_CMD install conda-lock -y
        fi

        # Check if environment already exists
        if $CONDA_CMD env list | grep -q "^metaxsfr "; then
            print_warning "conda environment 'metaxsfr' already exists"
            read -p "Remove existing environment? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_status "Removing existing environment..."
                $CONDA_CMD env remove -n metaxsfr -y
            else
                print_error "Installation cancelled"
                exit 1
            fi
        fi

        # Install using conda-lock
        print_status "Installing environment with conda-lock for platform: $PLATFORM..."
        conda-lock install -n metaxsfr "$LOCK_FILE"

    else
        print_warning "conda-lock.yml not found, falling back to environment.yml"
        ENV_FILE="environment.yml"
        if [ -f "$ENV_FILE" ]; then
            print_status "Using generic environment: $ENV_FILE"

            # Check if environment already exists
            if $CONDA_CMD env list | grep -q "^metaxsfr "; then
                print_warning "conda environment 'metaxsfr' already exists"
                read -p "Remove existing environment? [y/N] " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    print_status "Removing existing environment..."
                    $CONDA_CMD env remove -n metaxsfr -y
                else
                    print_error "Installation cancelled"
                    exit 1
                fi
            fi

            # Create conda environment
            print_status "Creating conda environment with $CONDA_CMD..."
            $CONDA_CMD env create -f "$ENV_FILE"
        else
            print_error "No environment file found!"
            exit 1
        fi
    fi

    # Get conda base path for activation
    CONDA_BASE=$(conda info --base)
    source "$CONDA_BASE/etc/profile.d/conda.sh"

    # Activate environment and install package
    print_status "Activating environment and installing METAXSFR..."
    conda activate metaxsfr
    pip install -e .

    # Test installation
    print_status "Testing installation..."
    if metaxsfr -h >/dev/null 2>&1; then
        print_success "METAXSFR installed successfully!"
        echo
        print_status "Installation directory: $INSTALL_DIR"
        echo
        print_status "To use METAXSFR:"
        echo "  1. Activate the environment: conda activate metaxsfr"
        echo "  2. Run metaxsfr: metaxsfr -h"
        echo "  3. Try with sample data: metaxsfr -r '$INSTALL_DIR/sample/bracken/*.txt' -t bracken -d gtdb -o results"
    else
        print_error "Installation test failed"
        exit 1
    fi
}

# Main execution
main() {
    cat << "EOF"
    __  __ ______ _______  __   __  _____ ______ _____  
   |  \/  |  ____|__   __| \ \ / / / ____|  ____|  __ \ 
   | \  / | |__     | |  /  \ V / | (___ | |__  | |__) |
   | |\/| |  __|    | | / /\ \ /   \___ \|  __| |  _  / 
   | |  | | |____   | |/ ____ | /  ____) | |    | | \ \ 
   |_|  |_|______|  |_|_/    \_V  |_____/|_|    |_|  \_\

Metagenome Taxonomic Explorer in a Single-File Report
EOF

    echo
    install_metaxsfr
}

# Run main function
main "$@"