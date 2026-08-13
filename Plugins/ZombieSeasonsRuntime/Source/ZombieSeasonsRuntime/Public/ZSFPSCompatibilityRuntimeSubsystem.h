#pragma once

#include "CoreMinimal.h"
#include "InputActionValue.h"
#include "Subsystems/WorldSubsystem.h"
#include "ZSFPSCompatibilityRuntimeSubsystem.generated.h"

class APawn;
class UCameraComponent;
class UChildActorComponent;
class UEnhancedInputComponent;
class UInputAction;

/**
 * Compatibility layer for the legacy Blueprint FPS controller.
 *
 * The existing Blueprint still owns forward/backward movement and horizontal
 * look. This layer binds to the same Enhanced Input actions and only supplies
 * the missing lateral movement and vertical camera/gun pitch.
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
    void EnsureInputBindings(APawn* PlayerPawn);
    void RefreshViewComponents(APawn* PlayerPawn);
    void HandleMoveInput(const FInputActionValue& Value);
    void HandleLookInput(const FInputActionValue& Value);
    void ApplyPitchToView(float PitchDeltaDegrees);

    TWeakObjectPtr<APawn> CachedPawn;
    TWeakObjectPtr<UEnhancedInputComponent> BoundInputComponent;
    TWeakObjectPtr<UCameraComponent> CachedCamera;
    TWeakObjectPtr<UChildActorComponent> CachedGun;

    TObjectPtr<UInputAction> MoveAction = nullptr;
    TObjectPtr<UInputAction> LookAction = nullptr;

    FRotator CameraBaseRotation = FRotator::ZeroRotator;
    FRotator GunBaseRotation = FRotator::ZeroRotator;
    float CurrentPitchDegrees = 0.0f;
    bool bGunInheritsCameraPitch = false;
};
