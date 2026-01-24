{ lib, ... }:
{
  options.features.full = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Enable all features";
    };
  };
}
