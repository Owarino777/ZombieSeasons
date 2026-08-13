#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ZSFPSInputRuntimeSubsystem.generated.h"

/**
 * Small compatibility layer for the legacy Blueprint FPS character.
 *
 * The existing Blueprint owns most FPS input, but its current graph does not
 * provide reliable AZERTY strafing or vertical mouse look. This subsystem only
 * fills those missing inputs so the binary Blueprint can remain untouched.
 */
UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSFPSInputRuntimeSubsystem final : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;

private:
    void InputPulse();

    FTimerHandle InputTimerHandle;
};
