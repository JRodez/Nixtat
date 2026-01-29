{
  description = "Analyze disk space used by packages in a nix store";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        lib = pkgs.lib;
        nixtat = import ./default.nix { inherit pkgs; };
      in
      {
        packages.default = nixtat;

        apps.default = {
          type = "app";
          program = lib.getExe nixtat;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: [ ps.rich ]))
            pkgs.coreutils
          ];
        };
      }
    );
}
