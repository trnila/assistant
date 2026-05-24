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
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      pyproject-nix,
      pyproject-build-systems,
      uv2nix,
      ...
    }:
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

        devShells.default = pkgs.mkShell {
          inputsFrom = [
            self.packages.${system}.frontend
            self.packages.${system}.backend
          ];
          packages = with pkgs; [
            git
            curl
          ];
        };
      }
    )
    // {
      nixosModules.default = import ./nix/module.nix self;
    };
}
