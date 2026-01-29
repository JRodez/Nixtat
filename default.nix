{
  pkgs ? import <nixpkgs> { },
  lib ? pkgs.lib,
  coreutils ? pkgs.coreutils,
  stdenv ? pkgs.stdenv,
  python3 ? pkgs.python3,
}:

let
  pythonEnv = python3.withPackages (
    ps: with ps; [
      rich
    ]
  );
in
stdenv.mkDerivation {
  pname = "nixdirstat";
  version = "0.1.0";
  src = ./.;

  buildInputs = [
    pythonEnv
    coreutils
  ];

  unpackPhase = ":";
  installPhase = "install -m755 -D $src/nixtat.py $out/bin/nixtat.py";

}
