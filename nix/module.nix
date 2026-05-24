self:

{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.lunch-assistant;
in
{
  options.services.lunch-assistant = {
    enable = lib.mkEnableOption "Lunch Assistant";

    # package = lib.mkOption {
    #   type = lib.types.package;
    #   default = self.packages.${pkgs.system}.default;
    # };
    #
    port = lib.mkOption {
      type = lib.types.port;
      default = 8080;
    };

    # host = lib.mkOption {
    #   type = lib.types.str;
    #   default = "0.0.0.0";
    # };
    #
    # environmentFile = lib.mkOption {
    #   type = lib.types.nullOr lib.types.path;
    #   default = null;
    # };
    #
    openFirewall = lib.mkOption {
      type = lib.types.bool;
      default = true;
    };

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/assistant";
    };
  };

  config = lib.mkIf cfg.enable {
    users.users.lunch-assistant = {
      isSystemUser = true;
      group = "lunch-assistant";
      home = cfg.dataDir;
      createHome = true;
    };

    users.groups.lunch-assistant = { };

    systemd.services.lunch-assistant = {
      description = "Lunch Assistant";
      after = [ "network-online.target" ];
      wantedBy = [ "multi-user.target" ];

      # environment = {
      #   PORT = toString cfg.port;
      #   HOST = cfg.host;
      # };

      serviceConfig = {
        Type = "simple";

        User = "lunch-assistant";
        Group = "lunch-assistant";

        WorkingDirectory = cfg.dataDir;

        ExecStart = ''
          ${self.packages.lunch-assistant}/bin/assistant
        '';

        Restart = "always";
        RestartSec = 5;

        StateDirectory = "assistant";
        RuntimeDirectory = "assistant";
        CacheDirectory = "assistant";

        NoNewPrivileges = true;
        PrivateTmp = true;
      };
    };
  };
}
