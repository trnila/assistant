{
  description = "Nix flake for trnila/assistant";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
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

    git-hooks.url = "github:cachix/git-hooks.nix";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      pyproject-nix,
      pyproject-build-systems,
      uv2nix,
      git-hooks,
      ...
    }@inputs:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        # will be <commit hash> or <commit hash-dirty> if containing unstaged changes
        version = self.rev or self.dirtyRev; # pass git commit as version

        backend = import ./nix/backend.nix {
          inherit
            version
            pkgs
            pyproject-nix
            uv2nix
            pyproject-build-systems
            ;
        };
      in
      {
        packages.frontend = backend.frontend;
        packages.backend = backend.backend;
        packages.runtime = backend.runtime;
        packages.app = backend.app;
        packages.default = backend.app;

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.app}/bin/lunchmenu";
        };

        devShells.default =
          let
            inherit (self.checks.${system}.pre-commit-check) shellHook enabledPackages;
          in
          pkgs.mkShell {
            inherit shellHook; # this installs the hooks automatically on `nix develop`
            nativeBuildInputs = with pkgs; [
              enabledPackages # the enabled hooks from "checks"
            ];
            inputsFrom = [
              self.packages.${system}.frontend
              self.packages.${system}.backend
            ];
            packages = with pkgs; [
              git
              curl
            ];
          };

        checks = {
          pre-commit-check = git-hooks.lib.${system}.run {
            src = ./.;
            hooks = {
              # keep-sorted start
              check-executables-have-shebangs.enable = true;
              check-yaml.enable = true;
              end-of-file-fixer.enable = true;
              keep-sorted.enable = true;
              mypy.enable = true;
              nixfmt.enable = true;
              ruff-format.enable = true;
              ruff.enable = true;
              shellcheck.enable = true;
              trim-trailing-whitespace.enable = true;
              # keep-sorted end
            };
            package = pkgs.prek;
          };
        };
      }
    )
    // {
      nixosModules.default = import ./nix/module.nix self;
    };
}
