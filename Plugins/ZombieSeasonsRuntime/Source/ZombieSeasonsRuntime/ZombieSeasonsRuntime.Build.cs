using UnrealBuildTool;

public class ZombieSeasonsRuntime : ModuleRules
{
    public ZombieSeasonsRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "AIModule",
                "NavigationSystem"
            }
        );
    }
}
