#include "ZSFPSCompatibilityRuntimeSubsystem.h"

#include "Camera/CameraComponent.h"
#include "Components/ChildActorComponent.h"
#include "EnhancedInputComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputAction.h"
#include "TimerManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogZombieSeasonsFPSCompatibility, Log, All);

namespace ZombieSeasonsFPSCompatibility
{
    static TAutoConsoleVariable<int32> CVarEnabled(
        TEXT("zs.FPSCompatibility"),
        1,
        TEXT("Enables the compatibility layer for legacy FPS strafe and vertical look."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarStrafeScale(
        TEXT("zs.StrafeScale"),
        1.0f,
        TEXT("Scale applied to the lateral component of INP_MoveAround."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarVerticalLookScale(
        TEXT("zs.VerticalLookScale"),
        1.0f,
        TEXT("Scale applied to the vertical component of INP_LookAround after IMC_FPS modifiers."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarMaxLookPitch(
        TEXT("zs.MaxLookPitch"),
        85.0f,
        TEXT("Maximum absolute first-person vertical look angle in degrees."),
        ECVF_Default);

    constexpr float BindingPulseSeconds = 0.25f;
}

void UZSFPSCompatibilityRuntimeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);

    MoveAction = LoadObject<UInputAction>(
        nullptr,
        TEXT("/Game/TopDownShooter/Core/Inputs/INP_MoveAround.INP_MoveAround"));
    LookAction = LoadObject<UInputAction>(
        nullptr,
        TEXT("/Game/TopDownShooter/Core/Inputs/INP_LookAround.INP_LookAround"));

    InWorld.GetTimerManager().SetTimer(
        BindingTimerHandle,
        this,
        &UZSFPSCompatibilityRuntimeSubsystem::BindingPulse,
        ZombieSeasonsFPSCompatibility::BindingPulseSeconds,
        true,
        0.05f);

    BindingPulse();

    UE_LOG(
        LogZombieSeasonsFPSCompatibility,
        Display,
        TEXT("ZombieSeasons FPS compatibility started. MoveAction=%s LookAction=%s"),
        *GetNameSafe(MoveAction),
        *GetNameSafe(LookAction));
}

void UZSFPSCompatibilityRuntimeSubsystem::Deinitialize()
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(BindingTimerHandle);
    }

    CachedPawn.Reset();
    BoundInputComponent.Reset();
    CachedCamera.Reset();
    CachedGun.Reset();
    MoveAction = nullptr;
    LookAction = nullptr;

    Super::Deinitialize();
}

void UZSFPSCompatibilityRuntimeSubsystem::BindingPulse()
{
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld() || !MoveAction || !LookAction)
    {
        return;
    }

    APlayerController* PlayerController = World->GetFirstPlayerController();
    APawn* PlayerPawn = PlayerController ? PlayerController->GetPawn() : nullptr;
    if (!IsValid(PlayerPawn))
    {
        return;
    }

    if (CachedPawn.Get() != PlayerPawn)
    {
        CachedPawn = PlayerPawn;
        BoundInputComponent.Reset();
        RefreshViewComponents(PlayerPawn);
    }

    UEnhancedInputComponent* EnhancedInput =
        PlayerPawn->FindComponentByClass<UEnhancedInputComponent>();

    if (!IsValid(EnhancedInput) || BoundInputComponent.Get() == EnhancedInput)
    {
        return;
    }

    EnhancedInput->BindAction(
        MoveAction,
        ETriggerEvent::Triggered,
        this,
        &UZSFPSCompatibilityRuntimeSubsystem::HandleMoveInput);

    EnhancedInput->BindAction(
        LookAction,
        ETriggerEvent::Triggered,
        this,
        &UZSFPSCompatibilityRuntimeSubsystem::HandleLookInput);

    BoundInputComponent = EnhancedInput;

    UE_LOG(
        LogZombieSeasonsFPSCompatibility,
        Display,
        TEXT("FPS compatibility bindings active. Pawn=%s Input=%s Camera=%s Gun=%s GunInheritsCameraPitch=%s"),
        *GetNameSafe(PlayerPawn),
        *GetNameSafe(EnhancedInput),
        *GetNameSafe(CachedCamera.Get()),
        *GetNameSafe(CachedGun.Get()),
        bGunInheritsCameraPitch ? TEXT("true") : TEXT("false"));
}

void UZSFPSCompatibilityRuntimeSubsystem::RefreshViewComponents(APawn* PlayerPawn)
{
    CachedCamera.Reset();
    CachedGun.Reset();
    bGunInheritsCameraPitch = false;
    CameraBaseRotation = FRotator::ZeroRotator;
    GunBaseRotation = FRotator::ZeroRotator;
    CurrentPitchDegrees = 0.0f;

    if (!IsValid(PlayerPawn))
    {
        return;
    }

    TArray<UCameraComponent*> Cameras;
    PlayerPawn->GetComponents<UCameraComponent>(Cameras);

    for (UCameraComponent* Camera : Cameras)
    {
        if (!IsValid(Camera))
        {
            continue;
        }

        if (Camera->GetFName() == TEXT("Camera"))
        {
            CachedCamera = Camera;
            break;
        }

        if (!CachedCamera.IsValid())
        {
            CachedCamera = Camera;
        }
    }

    TArray<UChildActorComponent*> ChildActors;
    PlayerPawn->GetComponents<UChildActorComponent>(ChildActors);

    for (UChildActorComponent* ChildActor : ChildActors)
    {
        if (IsValid(ChildActor) && ChildActor->GetFName() == TEXT("Gun"))
        {
            CachedGun = ChildActor;
            break;
        }
    }

    if (UCameraComponent* Camera = CachedCamera.Get())
    {
        CameraBaseRotation = Camera->GetRelativeRotation();
        CurrentPitchDegrees = FMath::ClampAngle(CameraBaseRotation.Pitch, -85.0f, 85.0f);
    }

    if (UChildActorComponent* Gun = CachedGun.Get())
    {
        GunBaseRotation = Gun->GetRelativeRotation();

        if (UCameraComponent* Camera = CachedCamera.Get())
        {
            for (USceneComponent* Parent = Gun->GetAttachParent(); Parent; Parent = Parent->GetAttachParent())
            {
                if (Parent == Camera)
                {
                    bGunInheritsCameraPitch = true;
                    break;
                }
            }
        }
    }
}

void UZSFPSCompatibilityRuntimeSubsystem::HandleMoveInput(const FInputActionValue& Value)
{
    APawn* PlayerPawn = CachedPawn.Get();
    if (!IsValid(PlayerPawn))
    {
        return;
    }

    const FVector2D MoveValue = Value.Get<FVector2D>();
    if (FMath::IsNearlyZero(MoveValue.X))
    {
        return;
    }

    const float StrafeScale =
        ZombieSeasonsFPSCompatibility::CVarStrafeScale.GetValueOnGameThread();

    PlayerPawn->AddMovementInput(
        PlayerPawn->GetActorRightVector(),
        MoveValue.X * StrafeScale,
        false);
}

void UZSFPSCompatibilityRuntimeSubsystem::HandleLookInput(const FInputActionValue& Value)
{
    const FVector2D LookValue = Value.Get<FVector2D>();
    if (FMath::IsNearlyZero(LookValue.Y))
    {
        return;
    }

    const float VerticalScale =
        ZombieSeasonsFPSCompatibility::CVarVerticalLookScale.GetValueOnGameThread();

    ApplyPitchToView(-LookValue.Y * VerticalScale);
}

void UZSFPSCompatibilityRuntimeSubsystem::ApplyPitchToView(float PitchDeltaDegrees)
{
    UCameraComponent* Camera = CachedCamera.Get();
    if (!IsValid(Camera))
    {
        return;
    }

    const float MaxPitch = FMath::Clamp(
        ZombieSeasonsFPSCompatibility::CVarMaxLookPitch.GetValueOnGameThread(),
        1.0f,
        89.0f);

    CurrentPitchDegrees = FMath::Clamp(
        CurrentPitchDegrees + PitchDeltaDegrees,
        -MaxPitch,
        MaxPitch);

    FRotator CameraRotation = CameraBaseRotation;
    CameraRotation.Pitch = CurrentPitchDegrees;
    Camera->SetRelativeRotation(CameraRotation);

    UChildActorComponent* Gun = CachedGun.Get();
    if (IsValid(Gun) && !bGunInheritsCameraPitch)
    {
        FRotator GunRotation = GunBaseRotation;
        GunRotation.Pitch += CurrentPitchDegrees - CameraBaseRotation.Pitch;
        Gun->SetRelativeRotation(GunRotation);
    }
}
