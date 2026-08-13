#pragma once

#include "CoreMinimal.h"
#include "InputActionValue.h"
#include "Subsystems/WorldSubsystem.h"
#include "ZSFPSCompatibilityRuntimeSubsystem.generated.h"

class APawn;
class APlayerController;
class UCameraComponent;
class UChildActorComponent;
class UEnhancedInputComponent;
class UInputAction;

/**
 * Compatibility layer for the legacy Blueprint FPS controller.
 *
 * The existing Blueprint keeps forward/backward movement and horizontal look.
 * This subsystem supplies deterministic AZERTY strafing and vertical camera /
 * weapon pitch without rewriting the binary Blueprint graph.
 */
UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSFPSCompatibilityRuntimeSubsystem final : public UTickableWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;

private:
    void BindingPulse();
    void RefreshViewComponents(APawn* PlayerPawn);
    void HandleLookInput(const FInputActionValue& Value);
    void ApplyPitchToView(float PitchDeltaDegrees);
    void ApplyResponsiveStrafe(APlayerController* PlayerController, APawn* PlayerPawn);

    TWeakObjectPtr<APawn> CachedPawn;
    TWeakObjectPtr<UEnhancedInputComponent> BoundInputComponent;
    TWeakObjectPtr<UCameraComponent> CachedCamera;
    TWeakObjectPtr<UChildActorComponent> CachedGun;

    UPROPERTY()
    TObjectPtr<UInputAction> LookAction = nullptr;

    FTimerHandle BindingTimerHandle;
    FRotator CameraBaseRotation = FRotator::ZeroRotator;
    FRotator GunBaseRotation = FRotator::ZeroRotator;
    float CurrentPitchDegrees = 0.0f;
    bool bGunInheritsCameraPitch = false;
};
