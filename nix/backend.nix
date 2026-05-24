{
  version,
  pkgs,
  pyproject-nix,
  uv2nix,
  pyproject-build-systems,
  ...
}:

let
  lib = pkgs.lib;
  frontend = pkgs.callPackage ./frontend.nix { inherit version pkgs; };

  # Following guide in https://pyproject-nix.github.io/uv2nix/usage/getting-started.html

  workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ../.; };

  # Automatically pick the right python interpreter
  # based on the value in pyproject.toml
  python = lib.head (
    pyproject-nix.lib.util.filterPythonInterpreters {
      inherit (workspace) requires-python;
      inherit (pkgs) pythonInterpreters;
    }
  );

  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };

  pythonBase = pkgs.callPackage pyproject-nix.build.packages {
    inherit python;
  };

  pythonSet = pythonBase.overrideScope (
    lib.composeManyExtensions [
      pyproject-build-systems.overlays.wheel
      overlay
    ]
  );

  backend = pythonSet.mkVirtualEnv "lunch" {
    lunchmenu = [ ]; # name from pyproject.toml
    # workspace.deps.default;
  };
  # End of following guide from uv2nix

  # Merge the backend with the index.html from frontend
  runtime = pkgs.stdenv.mkDerivation {
    pname = "lunchmenu-runtime";
    inherit version;

    src = ./.;

    installPhase = ''
      mkdir -p $out/
      cp -r ${backend}/* $out/
      cp ${frontend}/index.html $out/index.html
    '';
  };

  # Wrapper to serve Redis and run the backend
  app = pkgs.writeShellApplication {
    name = "lunchmenu";

    runtimeInputs = [
      pkgs.redis
      backend
      pkgs.netcat
    ];

    text = ''
      REDIS_PORT=6379
      REDIS_DIR=$(mktemp -d)

      cleanup() {
        if [ -n "$REDIS_PID" ]; then
          kill $REDIS_PID || true
        fi
        rm -rf "$REDIS_DIR"
      }

      trap cleanup EXIT

      redis-server \
        --port "$REDIS_PORT" \
        --dir "$REDIS_DIR" \
        --save "" \
        --appendonly no \
        &

      REDIS_PID=$!

      echo "Waiting for Redis..."

      until nc -z 127.0.0.1 "$REDIS_PORT"; do
        sleep 0.1
      done

      export REDIS_URL="redis://127.0.0.1:$REDIS_PORT"

      exec uvicorn backend.app:app \
        --host 0.0.0.0 \
        --port 8000
    '';
  };

in
{
  frontend = frontend;
  backend = backend;
  runtime = runtime;
  app = app;
}
