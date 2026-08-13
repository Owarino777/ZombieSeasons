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
 * The existing Blueprint keeps forward/backward movement and horizontal look.
 * This subsystem binds to the same Enhanced Input actions and only supplies
 * lateral movement plus vertical first-person camera/weapon pitch.
 */
UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSFPSCompatibilityRuntimeSubsystem final : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;

private:
    void BindingPulse();
    void RefreshViewComponents(APawn* PlayerPawn);
    void HandleMoveInput(const FInputActionValue& Value);
    void HandleLookInput(const FInputActionValue& Value);
    void ApplyPitchToView(float PitchDeltaDegrees);

    TWeakObjectPtr<APawn> CachedPawn;
    TWeakObjectPtr<UEnhancedInputComponent> BoundInputComponent;
    TWeakObjectPtr<UCameraComponent> CachedCamera;
    TWeakObjectPtr<UChildActorComponent> CachedGun;

    UPROPERTY()
    TObjectPtr<UInputAction> MoveAction = nullptr;

    UPROPERTY()
    TObjectPtr<UInputAction> LookAction = nullptr;

    FTimerHandle BindingTimerHandle;
    FRotator CameraBaseRotation = FRotator::ZeroRotator;
    FRotator GunBaseRotation = FRotator::ZeroRotator;
    float CurrentPitchDegrees = 0.0f;
    bool bGunInheritsCameraPitch = false;
};
