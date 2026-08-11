#include "ZSPlayerAimRuntimeSubsystem.h"

#include "CollisionQueryParams.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "HAL/IConsoleManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogZombieSeasonsAimRuntime, Log, All);

namespace ZombieSeasonsAimRuntime
{
    static TAutoConsoleVariable<int32> CVarAimCorrectionEnabled(
        TEXT("zs.AimCorrection"),
        1,
        TEXT("When non-zero, player BP_Projectile instances are redirected toward the actual player view."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarAimTraceDistance(
        TEXT("zs.AimTraceDistance"),
        100000.0f,
        TEXT("Maximum crosshair trace distance in centimeters for projectile aim correction."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarPlayerProjectileSpawnRadius(
        TEXT("zs.PlayerProjectileSpawnRadius"),
        1800.0f,
        TEXT("Maximum distance from a player pawn for a newly spawned BP_Projectile to be treated as a player shot."),
        ECVF_Default);
}

void UZSPlayerAimRuntimeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);

    ProjectileClass = LoadClass<AActor>(
        nullptr,
        TEXT("/Game/TopDownShooter/Core/Weapon/BP_Projectile.BP_Projectile_C"));

    if (!ProjectileClass)
    {
        UE_LOG(
            LogZombieSeasonsAimRuntime,
            Error,
            TEXT("Unable to load BP_Projectile generated class; player aim correction is disabled."));
        return;
    }

    ActorSpawnedHandle = InWorld.AddOnActorSpawnedHandler(
        FOnActorSpawned::FDelegate::CreateUObject(
            this,
            &UZSPlayerAimRuntimeSubsystem::HandleActorSpawned));

    UE_LOG(
        LogZombieSeasonsAimRuntime,
        Display,
        TEXT("ZombieSeasons player aim correction started. ProjectileClass=%s"),
        *GetNameSafe(ProjectileClass.Get()));
}

void UZSPlayerAimRuntimeSubsystem::Deinitialize()
{
    if (UWorld* World = GetWorld())
    {
        if (ActorSpawnedHandle.IsValid())
        {
            World->RemoveOnActorSpawnedHandler(ActorSpawnedHandle);
            ActorSpawnedHandle.Reset();
        }
    }

    ProjectileClass = nullptr;
    Super::Deinitialize();
}

void UZSPlayerAimRuntimeSubsystem::HandleActorSpawned(AActor* SpawnedActor)
{
    if (!IsValid(SpawnedActor)
        || !ProjectileClass
        || !SpawnedActor->IsA(ProjectileClass)
        || ZombieSeasonsAimRuntime::CVarAimCorrectionEnabled.GetValueOnGameThread() == 0)
    {
        return;
    }

    CorrectProjectileAim(SpawnedActor);
}

APlayerController* UZSPlayerAimRuntimeSubsystem::FindNearestPlayerController(const FVector& Location) const
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return nullptr;
    }

    APlayerController* BestController = nullptr;
    float BestDistanceSquared = TNumericLimits<float>::Max();

    for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
    {
        APlayerController* PlayerController = It->Get();
        APawn* PlayerPawn = PlayerController ? PlayerController->GetPawn() : nullptr;
        if (!IsValid(PlayerPawn))
        {
            continue;
        }

        const float DistanceSquared = FVector::DistSquared(Location, PlayerPawn->GetActorLocation());
        if (DistanceSquared < BestDistanceSquared)
        {
            BestDistanceSquared = DistanceSquared;
            BestController = PlayerController;
        }
    }

    const float MaxSpawnRadius = FMath::Max(
        0.0f,
        ZombieSeasonsAimRuntime::CVarPlayerProjectileSpawnRadius.GetValueOnGameThread());

    if (!BestController || BestDistanceSquared > FMath::Square(MaxSpawnRadius))
    {
        return nullptr;
    }

    return BestController;
}

void UZSPlayerAimRuntimeSubsystem::CorrectProjectileAim(AActor* Projectile)
{
    if (!IsValid(Projectile))
    {
        return;
    }

    APlayerController* PlayerController = FindNearestPlayerController(Projectile->GetActorLocation());
    if (!PlayerController)
    {
        return;
    }

    FVector ViewLocation = FVector::ZeroVector;
    FRotator ViewRotation = FRotator::ZeroRotator;
    PlayerController->GetPlayerViewPoint(ViewLocation, ViewRotation);

    const float TraceDistance = FMath::Max(
        1000.0f,
        ZombieSeasonsAimRuntime::CVarAimTraceDistance.GetValueOnGameThread());

    const FVector ViewForward = ViewRotation.Vector();
    const FVector TraceEnd = ViewLocation + ViewForward * TraceDistance;

    FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(ZombieSeasonsPlayerAim), true);
    QueryParams.AddIgnoredActor(Projectile);

    if (APawn* PlayerPawn = PlayerController->GetPawn())
    {
        QueryParams.AddIgnoredActor(PlayerPawn);
    }

    if (AActor* Owner = Projectile->GetOwner())
    {
        QueryParams.AddIgnoredActor(Owner);
    }

    FHitResult Hit;
    UWorld* World = GetWorld();
    const bool bHit = World && World->LineTraceSingleByChannel(
        Hit,
        ViewLocation,
        TraceEnd,
        ECC_Visibility,
        QueryParams);

    const FVector AimPoint = bHit ? Hit.ImpactPoint : TraceEnd;
    const FVector AimDirection = (AimPoint - Projectile->GetActorLocation()).GetSafeNormal();
    if (AimDirection.IsNearlyZero())
    {
        return;
    }

    Projectile->SetActorRotation(AimDirection.Rotation());

    UProjectileMovementComponent* ProjectileMovement =
        Projectile->FindComponentByClass<UProjectileMovementComponent>();
    if (!ProjectileMovement)
    {
        UE_LOG(
            LogZombieSeasonsAimRuntime,
            Warning,
            TEXT("Player projectile %s has no ProjectileMovementComponent; rotation corrected but velocity was not overridden."),
            *GetNameSafe(Projectile));
        return;
    }

    float Speed = ProjectileMovement->InitialSpeed;
    if (Speed <= KINDA_SMALL_NUMBER)
    {
        Speed = ProjectileMovement->Velocity.Size();
    }
    if (Speed <= KINDA_SMALL_NUMBER)
    {
        Speed = 3000.0f;
    }

    // The legacy BP_Projectile uses InitialVelocityInLocalSpace. Setting the actor
    // rotation first, then explicitly applying local +X velocity guarantees that the
    // projectile follows the camera/crosshair direction rather than the gun-arrow
    // transform. Player locomotion velocity is deliberately not added to the shot.
    ProjectileMovement->SetVelocityInLocalSpace(FVector(Speed, 0.0f, 0.0f));
    ProjectileMovement->UpdateComponentVelocity();

    UE_LOG(
        LogZombieSeasonsAimRuntime,
        VeryVerbose,
        TEXT("Aim-corrected projectile %s toward %s at speed %.1f"),
        *GetNameSafe(Projectile),
        *AimPoint.ToCompactString(),
        Speed);
}
