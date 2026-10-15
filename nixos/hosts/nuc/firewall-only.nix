# Keep a deployed system's packages unchanged while updating its generated
# firewall script. The caller must verify baseSystem is the live generation,
# review the script diff, and check the resulting closure before activation.
{ pkgs, baseSystem, oldStart, newStart }:
pkgs.replaceDependencies {
  drv = baseSystem;
  replacements = [
    {
      oldDependency = oldStart;
      newDependency = newStart;
    }
  ];
}
