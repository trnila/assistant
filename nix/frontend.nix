{ version, pkgs, ... }:

pkgs.stdenv.mkDerivation {
  pname = "lunch-assistant-frontend";
  inherit version;

  src = ../frontend;

  yarnOfflineCache = pkgs.fetchYarnDeps {
    yarnLock = ../frontend/yarn.lock;
    hash = "sha256-6xzFsvoGzzhizfDiHuzb4A3G1M48dNziJZ8PxcgOqFU=";
  };

  nativeBuildInputs = with pkgs; [
    yarnConfigHook
    yarnBuildHook
    yarnInstallHook
    # Needed for executing package.json scripts
    nodejs
  ];

  buildPhase = ''
    yarn build
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/
    cp -r dist/* $out/

    runHook postInstall
  '';
}
