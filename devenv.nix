{
  pkgs,
  lib,
  config,
  ...
}:
{
  languages = {
    python = {
      enable = true;
      uv.enable = true;
    };
    javascript = {
      enable = true;
      yarn.enable = true;
    };
  };

  # https://devenv.sh/services/
  services.redis.enable = true;

 processes = {
    web = {
      exec = "uv run fastapi dev";
      process-compose.depends_on.redis.condition = "process_healthy";
    };
    dev = {
      exec = "cd frontend && yarn install && yarn run dev";
    };
  };
}
