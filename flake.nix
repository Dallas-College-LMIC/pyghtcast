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

    # No nixpkgs follows: nix2container's patched skopeo must build against
    # its own pinned nixpkgs (the patch doesn't apply on current unstable).
    nix2container.url = "github:nlewo/nix2container";
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      git-hooks,
      nix2container,
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
      # Container image for the MCP server (linux only; deployed to k8s).
      # Pattern borrowed from persona-mcp: uv2nix virtualenv -> nix2container
      # layered image -> OCI archive that skopeo can push to a registry.
      packages = lib.genAttrs [ "x86_64-linux" "aarch64-linux" ] (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python313;
          n2c = nix2container.packages.${system}.nix2container;
          pythonBase = pkgs.callPackage pyproject-nix.build.packages { inherit python; };
          pythonSet = pythonBase.overrideScope (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.default
              overlay
              pyprojectOverrides
            ]
          );
          # Runtime env: base deps + the [mcp] extra. No dev tools in the image.
          virtualenvProd = pythonSet.mkVirtualEnv "pyghtcast-prod-env" (
            workspace.deps.default
            // {
              pyghtcast = (workspace.deps.default.pyghtcast or [ ]) ++ [ "mcp" ];
            }
          );
          containerEntrypoint = pkgs.writeShellScript "pyghtcast-mcp-entrypoint" ''
            unset PYTHONPATH
            exec ${virtualenvProd}/bin/pyghtcast-mcp \
              --transport streamable-http \
              --host 0.0.0.0 \
              --port 8080
          '';
          container = n2c.buildImage {
            name = "pyghtcast-mcp";
            config = {
              entrypoint = [ "${containerEntrypoint}" ];
              ExposedPorts."8080/tcp" = { };
            };
            layers = [
              (n2c.buildLayer {
                deps = [ virtualenvProd ];
                maxLayers = 80;
              })
            ];
          };
          containerOCI =
            pkgs.runCommand "pyghtcast-mcp-oci"
              {
                nativeBuildInputs = [ nix2container.packages.${system}.skopeo-nix2container ];
              }
              ''
                skopeo --insecure-policy copy nix:${container} oci:$out:latest --tmpdir $TMPDIR
              '';
        in
        {
          inherit virtualenvProd container containerOCI;
          skopeo = nix2container.packages.${system}.skopeo-nix2container;
          default = containerOCI;
        }
      );

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
                # Run mypy from a self-contained nix python env carrying the
                # type stubs and mcp, so the hook resolves
                # pandas/requests/click/mcp instead of treating them as Any.
                # A `uv run`-based hook would be nicer (uv = single source of
                # truth) but it cannot run in the pure sandbox that
                # `nix flake check` / pre-commit-check use (no /bin/sh, no
                # network, no .venv), so we keep the self-contained nix env.
                settings.binPath = "${pkgs.python313.withPackages (p: [
                  p.mypy
                  p.pandas-stubs
                  p.types-requests
                  p.types-click
                  p.mcp
                ])}/bin/mypy";
                # nixpkgs ships mcp 1.12.4 while the project pins >=1.27
                # (runtime 1.28.1). The FastMCP API surface mypy inspects
                # (FastMMP ctor, @tool, .run) is identical across both versions,
                # so this typechecks the same things; uv remains the source of
                # truth for the dev workflow (`uv run --extra dev mypy pyghtcast`).
                # Type-check the library only (matches `mypy pyghtcast`):
                # tests aren't shipped library code and pre-commit passes their
                # paths to mypy as bare module names, which breaks per-module
                # config overrides.
                files = "^pyghtcast/";
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
