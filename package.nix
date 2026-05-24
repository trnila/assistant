{
  pkgs,
  pyproject-nix,
  uv2nix,
  pyproject-build-systems,
  ...
}:

let
  lib = pkgs.lib;

  version = "unstable-2026-05-24";

  # Following guide in https://pyproject-nix.github.io/uv2nix/usage/getting-started.html

  workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./backend; };

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

  backend = pythonSet.mkVirtualEnv "lunch" workspace.deps.default;

  backendApp = pkgs.writeShellApplication {
    name = "lunchmenu-backend";

    runtimeInputs = [
      python
    ];

    text = ''
      exec uvicorn lunchmenu.app:app --host 0.0.0.0 --port 8000
    '';
  };

  # project = pyproject-nix.lib.project.loadPyproject {
  #   projectRoot = ./.;
  # };
  # # arg = project.renderers.withPackages { inherit python; };
  # # pythonEnv = python.withPackages arg;
  # attrs = project.renderers.buildPythonPackage { inherit python; };
  # backend = python.pkgs.buildPythonPackage (attrs);

  # backend = pkgs.stdenv.mkDerivation {
  #   pname = thisProjectAsNixPkg.pname;
  #   version = thisProjectAsNixPkg.version;
  #   src = ./.; // Source of your main script
  #
  #   nativeBuildInputs = [ pkgs.makeWrapper ];
  # buildInputs = [ appPythonEnv ]; // Runtime Python environment
  #
  # installPhase = ''
  #   mkdir -p $out/bin
  #   cp main.py $out/bin/${thisProjectAsNixPkg.pname}-script
  #   chmod +x $out/bin/${thisProjectAsNixPkg.pname}-script
  #   makeWrapper ${appPythonEnv}/bin/python $out/bin/${thisProjectAsNixPkg.pname} \
  #     --add-flags $out/bin/${thisProjectAsNixPkg.pname}-script
  #     '';
  # };

  bak = pkgs.stdenv.mkDerivation {
    pname = "assistant-backend";
    version = "unstable";

    src = lib.cleanSource ./lunchmenu;

    nativeBuildInputs = [
      pkgs.uv
      pkgs.python3
    ];

    buildInputs = [
      pkgs.poppler-utils
      pkgs.tesseract
      # pkgs.tesseract5Languages.ces
      pkgs.tzdata
    ];

    buildPhase = ''
      export HOME=$TMPDIR
      export UV_NO_CACHE=1

      # install exactly like Docker
      uv sync --no-dev --frozen
    '';

    installPhase = ''
      mkdir -p $out/lunchmenu
      cp -r . $out/lunchmenu
    '';
  };

in
{
  inherit backend;
  # inherit project attrs;
  inherit overlay;
  inherit bak;
  inherit backendApp;
  # inherit frontend backend;
  # lunch-assistant = pkgs.symlinkJoin {
  #   name = "assistant";
  #
  #   paths = [
  #     frontend
  #     # backend
  #   ];
  #
  #   buildInputs = [ pkgs.makeWrapper ];
  #
  #   postBuild = ''
  #     mkdir -p $out/bin
  #
  #     makeWrapper ${backend}/bin/uvicorn $out/bin/assistant \
  #       --add-flags "main:app" \
  #       --add-flags "--host 0.0.0.0" \
  #       --add-flags "--port 8080" \
  #       --set FRONTEND_DIST ${frontend}/share/frontend
  #   '';
  # };
}
