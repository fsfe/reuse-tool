# SPDX-FileCopyrightText: 2018 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

{
  description =
    "reuse is a tool for compliance with the REUSE recommendations.";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    {
      # Nixpkgs overlay providing the application
      overlay = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlay
        (final: prev: {
          # The application
          reuse = prev.poetry2nix.mkPoetryApplication {
            projectDir = ./.;
            overrides = prev.poetry2nix.overrides.withDefaults (self: super: {
              # license-expression override
              license-expression = super.license-expression.overridePythonAttrs
                (old: {
                  dontConfigure = true;
                  buildInputs = old.buildInputs
                    ++ [ self.boolean-py self.setuptools-scm ];
                });
            });
          };
        })
      ];
    } // (flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlay ];
        };
      in rec {
        # Executed by `nix check .#<name>`
        checks = flake-utils.lib.flattenTree { reuse = pkgs.reuse; };
        # Executed by `nix build .#<name>`
        packages = flake-utils.lib.flattenTree {
          reuse = pkgs.reuse;
          docker-image = pkgs.dockerTools.buildLayeredImage {
            name = "fsfe/reuse";
            tag = "latest";
            created = "now";
            contents = [ pkgs.reuse pkgs.git pkgs.mercurial ];
            fakeRootCommands = "mkdir -p /data";
            config = {
              Cmd = "lint";
              EntryPoint = "${pkgs.reuse}/bin/reuse";
              WorkingDir = "/data";
            };
          };
        };
        defaultPackage = packages.reuse;
        # Executed by `nix run .#<name>`
        apps.reuse = flake-utils.lib.mkApp { drv = packages.reuse; };
        defaultApp = apps.reuse;
        # Development shell
        devShell = let
          reuseEnv = pkgs.poetry2nix.mkPoetryEnv {
            projectDir = ./.;
            editablePackageSources = {
              # To develop reuse in editable mode, run
              # 'nix develop --impure'
              reuse = "${builtins.getEnv "PWD"}/src";
            };
            overrides = pkgs.poetry2nix.overrides.withDefaults (self: super: {
              # license-expression override
              license-expression = super.license-expression.overridePythonAttrs
                (old: {
                  dontConfigure = true;
                  buildInputs = old.buildInputs
                    ++ [ self.boolean-py self.setuptools-scm ];
                });
            });
          };
        in pkgs.mkShell {
          buildInputs =
            [ reuseEnv pkgs.poetry pkgs.nodePackages.pyright pkgs.gh ];
        };
      }));
}
