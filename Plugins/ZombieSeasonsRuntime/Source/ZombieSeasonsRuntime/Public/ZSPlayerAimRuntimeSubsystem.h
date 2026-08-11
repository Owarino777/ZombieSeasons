#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ZSPlayerAimRuntimeSubsystem.generated.h"

class AActor;
class APlayerController;

/**
 * Runtime correction layer for the legacy FPS projectile Blueprint.
 *
 * The original BP_Gun/BP_Projectile firing graph is binary and cannot be safely
 * rewritten from editor automation. This subsystem keeps the existing weapon,
 * muzzle and projectile assets intact, but redirects newly spawned player
 * projectiles toward the actual player view / crosshair direction.
 */
UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSPlayerAimRuntimeSubsystem final : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;

private:
    void HandleActorSpawned(AActor* SpawnedActor);
    void CorrectProjectileAim(AActor* Projectile);
    APlayerController* FindNearestPlayerController(const FVector& Location) const;

    TSubclassOf<AActor> ProjectileClass;
    FDelegateHandle ActorSpawnedHandle;
};
