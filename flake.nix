{
  description = "Pyghtcast - Python wrapper for Lightcast API";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      git-hooks,
      ...
    }:
    let
      inherit (nixpkgs) lib;

      # Support multiple systems
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
      pyprojectOverrides = _final: _prev: {
        # Implement build fixups here if needed
      };
    in
    {
      # Pre-commit hooks configuration
      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          pre-commit-check = git-hooks.lib.${system}.run {
            src = ./.;
            hooks = {
              # Python formatters and linters
              ruff = {
                enable = true;
                # Linting with auto-fix
              };
              ruff-format = {
                enable = true;
                # Formatting
              };
              mypy = {
                enable = true;
                # Type checking
              };

              # General file hygiene
              trim-trailing-whitespace.enable = true;
              end-of-file-fixer.enable = true;
              check-merge-conflicts.enable = true;
              check-added-large-files = {
                enable = true;
                args = [ "--maxkb=5000" ];
              };
              check-yaml.enable = true;
              check-json.enable = true;
              check-toml.enable = true;
              check-python.enable = true; # Check Python AST
            };
          };
        }
      );

      apps = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          setupScript = pkgs.writeScriptBin "setup" ''
            #!${pkgs.bash}/bin/bash
            set -euo pipefail

            # Initialize UV environment
            echo "Initializing UV environment..."
            ${pkgs.uv}/bin/uv venv
            ${pkgs.uv}/bin/uv sync
            echo "✓ UV environment initialized"

            # Note: Pre-commit hooks are automatically installed via git-hooks.nix
            # when entering the development shell

            # Success message
            echo
            echo "✅ Project initialized successfully!"
            echo
            echo "Note: Pre-commit hooks are automatically configured when you enter the dev shell."
            echo
          '';
        in
        {
          setup = {
            type = "app";
            program = "${setupScript}/bin/setup";
          };
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python313;  # Updated to Python 3.13
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              # Python and package management
              python
              pkgs.uv

              # Development tools
              pkgs.ruff  # Latest ruff with Python 3.13 support

              # System libraries for numpy/pandas
              pkgs.stdenv.cc.cc.lib
              pkgs.zlib
            ]
            ++ (with pkgs.python313Packages; [
              mypy
              debugpy
              python-lsp-server
              python-lsp-ruff
              pylsp-mypy
            ])
            # Add pre-commit enabled packages
            ++ self.checks.${system}.pre-commit-check.enabledPackages;

            env = {
              UV_PYTHON_DOWNLOADS = "never";
              UV_PYTHON = python.interpreter;
              # Keep the Lightcast API environment variables
              LCAPI_USER = "";
              LCAPI_PASS = "";
            };

            shellHook = ''
              # Run the pre-commit shellHook first
              ${self.checks.${system}.pre-commit-check.shellHook}

              echo "🐍 Python Development Environment - Pyghtcast"
              echo "Python: ${python.version}"

              # Set up environment
              unset PYTHONPATH
              export PYTHONPATH="$PWD:$PYTHONPATH"

              # Set LD_LIBRARY_PATH for numpy and other C extensions
              export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib:$LD_LIBRARY_PATH"

              # Python virtual environment setup
              if [[ ! -d .venv ]]; then
                echo "Creating Python virtual environment..."
                uv venv
                uv sync
              else
                source .venv/bin/activate
                # Only sync if pyproject.toml is newer than .venv
                if [[ pyproject.toml -nt .venv ]]; then
                  echo "Dependencies may have changed, running uv sync..."
                  uv sync
                fi
              fi

              echo ""
              echo "📦 Pyghtcast - Lightcast API Python wrapper"
              echo "To run examples: python -m pyghtcast.examples.skills_example"
              echo ""
            '';
          };
        }
      );
    };
}
