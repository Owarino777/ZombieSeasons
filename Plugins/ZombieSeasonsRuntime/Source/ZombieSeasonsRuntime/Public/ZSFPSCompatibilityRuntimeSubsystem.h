#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ZSFPSCompatibilityRuntimeSubsystem.generated.h"

class APawn;
class UCameraComponent;
class UChildActorComponent;

/**
 * Compatibility layer for the legacy Blueprint FPS controller.
 *
 * It only fills gaps that are not reliable in the current Blueprint graph:
 * AZERTY strafing and vertical mouse look. Forward/backward movement and yaw
 * remain owned by the existing Blueprint input setup.
 */
UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSFPSCompatibilityRuntimeSubsystem final : public UTickableWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;

private:
    void RefreshCachedComponents(APawn* PlayerPawn);
    void ApplyStrafe(APawn* PlayerPawn) const;
    void ApplyVerticalLook();

    TWeakObjectPtr<APawn> CachedPawn;
    TWeakObjectPtr<UCameraComponent> CachedCamera;
    TWeakObjectPtr<UChildActorComponent> CachedGun;

    FRotator CameraBaseRotation = FRotator::ZeroRotator;
    FRotator GunBaseRotation = FRotator::ZeroRotator;
    float CurrentPitchDegrees = 0.0f;
    bool bGunInheritsCameraPitch = false;
};
