#include "ZSGameplayRuntimeSubsystem.h"

#include "AIController.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Modules/ModuleManager.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "UObject/UObjectGlobals.h"

DEFINE_LOG_CATEGORY_STATIC(LogZombieSeasonsRuntime, Log, All);

namespace ZombieSeasonsRuntime
{
    static TAutoConsoleVariable<int32> CVarMaxActiveEnemies(
        TEXT("zs.MaxActiveEnemies"),
        50,
        TEXT("Maximum number of enemies spawned by the ZombieSeasons runtime subsystem."),
        ECVF_Default);

    static TAutoConsoleVariable<int32> CVarAmbientSpawnsPerPulse(
        TEXT("zs.AmbientSpawnsPerPulse"),
        2,
        TEXT("Maximum ambient enemies spawned per runtime pulse."),
        ECVF_Default);

    static TAutoConsoleVariable<int32> CVarHordeBurstSize(
        TEXT("zs.HordeBurstSize"),
        20,
        TEXT("Target number of enemies spawned when a horde trigger activates."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarSpawnActivationRadius(
        TEXT("zs.SpawnActivationRadius"),
        7000.0f,
        TEXT("Maximum player distance in centimeters for ambient spawn activation."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarMinimumSpawnDistance(
        TEXT("zs.MinimumSpawnDistance"),
        2200.0f,
        TEXT("Minimum player distance in centimeters for ambient spawning."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarDespawnDistance(
        TEXT("zs.DespawnDistance"),
        28000.0f,
        TEXT("Runtime-spawned enemies farther than this from all players are recycled."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarHordeTriggerRadius(
        TEXT("zs.HordeTriggerRadius"),
        2500.0f,
        TEXT("Player distance in centimeters that activates a horde marker."),
        ECVF_Default);

    static TAutoConsoleVariable<float> CVarObjectiveInteractionRadius(
        TEXT("zs.ObjectiveInteractionRadius"),
        350.0f,
        TEXT("Automatic greybox objective interaction radius in centimeters."),
        ECVF_Default);

    static TAutoConsoleVariable<int32> CVarAutoObjectives(
        TEXT("zs.AutoObjectives"),
        1,
        TEXT("When non-zero, greybox objectives complete through proximity or horde-clear rules."),
        ECVF_Default);

    constexpr float RuntimePulseSeconds = 0.75f;
    constexpr float MarkerRescanIntervalSeconds = 2.0f;
    constexpr float NavigationProjectionExtentXY = 600.0f;
    constexpr float NavigationProjectionExtentZ = 1000.0f;
    constexpr float HordeSpawnSearchRadius = 14000.0f;
    constexpr float ExtractionEndpointRadius = 500.0f;
    const FVector ExtractionEndpoint(88000.0f, -18000.0f, 1200.0f);
}

void UZSGameplayRuntimeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);

    if (InWorld.GetNetMode() == NM_Client)
    {
        return;
    }

    // School owns its local progression; legacy worlds retain their existing behavior.
    if (InWorld.GetWorldSettings()->ActorHasTag(TEXT("ZS.Scenario.School")))
    {
        UE_LOG(LogZombieSeasonsRuntime, Display, TEXT("Legacy map objectives disabled for school scenario."));
        return;
    }

    LoadGameplayClasses();
    InitializeObjectiveSequence();
    ScanGameplayMarkers();

    InWorld.GetTimerManager().SetTimer(
        RuntimeTimerHandle,
        this,
        &UZSGameplayRuntimeSubsystem::RuntimePulse,
        ZombieSeasonsRuntime::RuntimePulseSeconds,
        true,
        0.35f);

    UE_LOG(
        LogZombieSeasonsRuntime,
        Display,
        TEXT("ZombieSeasons runtime started. Loaded markers=%d EnemyClass=%s AIControllerClass=%s CurrentObjective=%s"),
        Markers.Num(),
        *GetNameSafe(EnemyClass.Get()),
        *GetNameSafe(EnemyControllerClass.Get()),
        *GetCurrentObjectiveId().ToString());

    if (GetCurrentObjectiveId() != NAME_None)
    {
        OnObjectiveChanged.Broadcast(GetCurrentObjectiveId(), CurrentObjectiveIndex);
    }
}

void UZSGameplayRuntimeSubsystem::Deinitialize()
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(RuntimeTimerHandle);
    }

    SpawnedEnemies.Reset();
    Markers.Reset();
    MarkerIndexById.Reset();
    ActivatedHordes.Reset();
    ActiveHordes.Reset();
    CompletedObjectives.Reset();
    DefenseObjectiveHordes.Reset();
    ObjectiveSequence.Reset();

    Super::Deinitialize();
}

void UZSGameplayRuntimeSubsystem::LoadGameplayClasses()
{
    EnemyClass = LoadClass<APawn>(
        nullptr,
        TEXT("/Game/TopDownShooter/Core/BP_Enemy.BP_Enemy_C"));

    EnemyControllerClass = LoadClass<AAIController>(
        nullptr,
        TEXT("/Game/TopDownShooter/Core/AIC_Enemy.AIC_Enemy_C"));

    if (!EnemyClass)
    {
        UE_LOG(LogZombieSeasonsRuntime, Error, TEXT("Unable to load BP_Enemy generated class."));
    }

    if (!EnemyControllerClass)
    {
        UE_LOG(LogZombieSeasonsRuntime, Error, TEXT("Unable to load AIC_Enemy generated class."));
    }
}

void UZSGameplayRuntimeSubsystem::InitializeObjectiveSequence()
{
    ObjectiveSequence = {
        TEXT("Hub.Objective.InitialEquipment"),
        TEXT("Hub.Objective.ObjectiveBoard"),
        TEXT("Spring.Objective.RelayApproach"),
        TEXT("Spring.Objective.RelayPower"),
        TEXT("Spring.Objective.RelayRepair"),
        TEXT("Spring.Objective.DistrictKey"),
        TEXT("Spring.Objective.HubShortcutUnlock"),
        TEXT("Summer.Objective.FuelPickup"),
        TEXT("Summer.Objective.BatteryPickup"),
        TEXT("Summer.Objective.ServiceGateControl"),
        TEXT("Autumn.Objective.InfrastructureRecords"),
        TEXT("Autumn.Objective.ArmoryAccess"),
        TEXT("Autumn.Objective.PoliceDefenseStart"),
        TEXT("Autumn.Objective.PoliceDefenseComplete"),
        TEXT("Winter.Objective.PowerStationEntry"),
        TEXT("Winter.Objective.PowerSwitchA"),
        TEXT("Winter.Objective.PowerSwitchB"),
        TEXT("Winter.Objective.MainBreaker"),
        TEXT("Winter.Objective.DamControls"),
        TEXT("Winter.Objective.ServiceRoadGate"),
        TEXT("Extraction.Objective.PerimeterEntry"),
        TEXT("Extraction.Objective.ControlBuilding"),
        TEXT("Extraction.Objective.DefenseA"),
        TEXT("Extraction.Objective.DefenseB"),
        TEXT("Extraction.Objective.FinalCrossing")
    };

    CurrentObjectiveIndex = 0;
    CompletedObjectives.Reset();
    DefenseObjectiveHordes.Reset();
    bExtractionReady = false;
    bExtractionCompleted = false;
}

void UZSGameplayRuntimeSubsystem::RuntimePulse()
{
    UWorld* World = GetWorld();
    if (!World || World->GetNetMode() == NM_Client)
    {
        return;
    }

    static double LastMarkerRescanSeconds = -1000.0;
    const double Now = World->GetTimeSeconds();
    if ((Now - LastMarkerRescanSeconds) >= ZombieSeasonsRuntime::MarkerRescanIntervalSeconds)
    {
        ScanGameplayMarkers();
        LastMarkerRescanSeconds = Now;
    }

    const TArray<APawn*> PlayerPawns = GatherPlayerPawns();
    if (PlayerPawns.IsEmpty())
    {
        return;
    }

    PruneAndDespawnEnemies(PlayerPawns);
    ProcessAutomaticHordeTriggers(PlayerPawns);
    ProcessAmbientSpawning(PlayerPawns);
    ProcessCurrentObjective(PlayerPawns);
    ProcessExtraction(PlayerPawns);
}

void UZSGameplayRuntimeSubsystem::ScanGameplayMarkers()
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    const FName GameplayStageTag(TEXT("ZS.Stage.GameplayLayout"));

    for (TActorIterator<ATargetPoint> It(World); It; ++It)
    {
        ATargetPoint* Actor = *It;
        if (!IsValid(Actor) || !ActorHasExactTag(Actor, GameplayStageTag))
        {
            continue;
        }

        FName StableId = NAME_None;
        FName Role = NAME_None;
        FName District = NAME_None;
        FName SpawnGroup = NAME_None;

        if (!ExtractPrefixedTag(Actor, TEXT("ZS.Id."), StableId) || StableId == NAME_None)
        {
            continue;
        }

        ExtractPrefixedTag(Actor, TEXT("ZS.MarkerType."), Role);
        ExtractPrefixedTag(Actor, TEXT("ZS.District."), District);
        ExtractPrefixedTag(Actor, TEXT("ZS.SpawnGroup."), SpawnGroup);

        if (const int32* ExistingIndex = MarkerIndexById.Find(StableId))
        {
            FMarkerRecord& Existing = Markers[*ExistingIndex];
            Existing.Actor = Actor;
            Existing.Location = Actor->GetActorLocation();
            Existing.Role = Role;
            Existing.District = District;
            Existing.SpawnGroup = SpawnGroup;
        }
        else
        {
            FMarkerRecord Record;
            Record.Actor = Actor;
            Record.StableId = StableId;
            Record.Role = Role;
            Record.District = District;
            Record.SpawnGroup = SpawnGroup;
            Record.Location = Actor->GetActorLocation();

            const int32 NewIndex = Markers.Add(MoveTemp(Record));
            MarkerIndexById.Add(StableId, NewIndex);
        }

        if (Role == TEXT("SafeZoneContract"))
        {
            FName RadiusTag = NAME_None;
            if (ExtractPrefixedTag(Actor, TEXT("ZS.SafeZoneRadius."), RadiusTag))
            {
                const float ParsedRadius = FCString::Atof(*RadiusTag.ToString());
                if (ParsedRadius > 0.0f)
                {
                    SafeZoneRadiusCm = ParsedRadius;
                }
            }
        }
    }
}

TArray<APawn*> UZSGameplayRuntimeSubsystem::GatherPlayerPawns() const
{
    TArray<APawn*> Result;
    UWorld* World = GetWorld();
    if (!World)
    {
        return Result;
    }

    for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
    {
        const APlayerController* PlayerController = It->Get();
        if (!PlayerController)
        {
            continue;
        }

        APawn* Pawn = PlayerController->GetPawn();
        if (IsValid(Pawn))
        {
            Result.Add(Pawn);
        }
    }

    return Result;
}

float UZSGameplayRuntimeSubsystem::DistanceToNearestPlayer(
    const FVector& Location,
    const TArray<APawn*>& PlayerPawns) const
{
    float BestDistance = TNumericLimits<float>::Max();
    for (const APawn* PlayerPawn : PlayerPawns)
    {
        if (IsValid(PlayerPawn))
        {
            BestDistance = FMath::Min(BestDistance, FVector::Dist(Location, PlayerPawn->GetActorLocation()));
        }
    }
    return BestDistance;
}

void UZSGameplayRuntimeSubsystem::PruneAndDespawnEnemies(const TArray<APawn*>& PlayerPawns)
{
    const float DespawnDistance = ZombieSeasonsRuntime::CVarDespawnDistance.GetValueOnGameThread();

    for (int32 Index = SpawnedEnemies.Num() - 1; Index >= 0; --Index)
    {
        FSpawnedEnemyRecord& Record = SpawnedEnemies[Index];
        APawn* Pawn = Record.Pawn.Get();
        if (!IsValid(Pawn))
        {
            SpawnedEnemies.RemoveAtSwap(Index);
            continue;
        }

        const FVector Location = Pawn->GetActorLocation();
        const bool bInsideProtectedHub = FVector2D(Location.X, Location.Y).Size() < SafeZoneRadiusCm;
        const float PlayerDistance = DistanceToNearestPlayer(Location, PlayerPawns);

        if (bInsideProtectedHub)
        {
            Pawn->Destroy();
            SpawnedEnemies.RemoveAtSwap(Index);
            continue;
        }

        if (PlayerDistance > DespawnDistance)
        {
            ReleaseSourceMarker(Record.SourceMarkerId);
            Pawn->Destroy();
            SpawnedEnemies.RemoveAtSwap(Index);
        }
    }

    TArray<FName> ClearedHordes;
    for (const FName HordeId : ActiveHordes)
    {
        if (IsHordeCleared(HordeId))
        {
            ClearedHordes.Add(HordeId);
        }
    }
    for (const FName HordeId : ClearedHordes)
    {
        ActiveHordes.Remove(HordeId);
        UE_LOG(LogZombieSeasonsRuntime, Display, TEXT("Horde cleared: %s"), *HordeId.ToString());
    }
}

void UZSGameplayRuntimeSubsystem::ProcessAutomaticHordeTriggers(const TArray<APawn*>& PlayerPawns)
{
    const float TriggerRadius = ZombieSeasonsRuntime::CVarHordeTriggerRadius.GetValueOnGameThread();

    TArray<FName> ToActivate;
    for (const FMarkerRecord& Marker : Markers)
    {
        if (Marker.Role != TEXT("HordeTrigger") || ActivatedHordes.Contains(Marker.StableId) || !Marker.Actor.IsValid())
        {
            continue;
        }

        if (DistanceToNearestPlayer(Marker.Location, PlayerPawns) <= TriggerRadius)
        {
            ToActivate.Add(Marker.StableId);
        }
    }

    for (const FName HordeId : ToActivate)
    {
        ActivateHordeInternal(HordeId);
    }
}

void UZSGameplayRuntimeSubsystem::ProcessAmbientSpawning(const TArray<APawn*>& PlayerPawns)
{
    if (!EnemyClass)
    {
        return;
    }

    const int32 MaxActive = FMath::Max(0, ZombieSeasonsRuntime::CVarMaxActiveEnemies.GetValueOnGameThread());
    const int32 RemainingCapacity = MaxActive - GetActiveEnemyCount();
    if (RemainingCapacity <= 0)
    {
        return;
    }

    const int32 SpawnBudget = FMath::Min(
        RemainingCapacity,
        FMath::Max(0, ZombieSeasonsRuntime::CVarAmbientSpawnsPerPulse.GetValueOnGameThread()));
    if (SpawnBudget <= 0)
    {
        return;
    }

    const float MinimumDistance = ZombieSeasonsRuntime::CVarMinimumSpawnDistance.GetValueOnGameThread();
    const float MaximumDistance = ZombieSeasonsRuntime::CVarSpawnActivationRadius.GetValueOnGameThread();

    struct FCandidate
    {
        int32 MarkerIndex = INDEX_NONE;
        float Distance = 0.0f;
    };

    TArray<FCandidate> Candidates;
    for (int32 Index = 0; Index < Markers.Num(); ++Index)
    {
        const FMarkerRecord& Marker = Markers[Index];
        if (Marker.Role != TEXT("ZombieSpawnCandidate") || Marker.bConsumed || !Marker.Actor.IsValid())
        {
            continue;
        }

        if (FVector2D(Marker.Location.X, Marker.Location.Y).Size() < SafeZoneRadiusCm)
        {
            continue;
        }

        const float Distance = DistanceToNearestPlayer(Marker.Location, PlayerPawns);
        if (Distance >= MinimumDistance && Distance <= MaximumDistance)
        {
            Candidates.Add({Index, Distance});
        }
    }

    Candidates.Sort([](const FCandidate& Left, const FCandidate& Right)
    {
        if (!FMath::IsNearlyEqual(Left.Distance, Right.Distance))
        {
            return Left.Distance < Right.Distance;
        }
        return Left.MarkerIndex < Right.MarkerIndex;
    });

    int32 Spawned = 0;
    for (const FCandidate& Candidate : Candidates)
    {
        if (Spawned >= SpawnBudget)
        {
            break;
        }

        if (Markers.IsValidIndex(Candidate.MarkerIndex) && SpawnEnemyFromMarker(Markers[Candidate.MarkerIndex]))
        {
            ++Spawned;
        }
    }
}

void UZSGameplayRuntimeSubsystem::ProcessCurrentObjective(const TArray<APawn*>& PlayerPawns)
{
    if (ZombieSeasonsRuntime::CVarAutoObjectives.GetValueOnGameThread() == 0)
    {
        return;
    }

    const FName ObjectiveId = GetCurrentObjectiveId();
    if (ObjectiveId == NAME_None)
    {
        return;
    }

    FMarkerRecord* Marker = FindMarker(ObjectiveId);
    if (!Marker || !Marker->Actor.IsValid())
    {
        return;
    }

    const float InteractionRadius = ZombieSeasonsRuntime::CVarObjectiveInteractionRadius.GetValueOnGameThread();
    if (DistanceToNearestPlayer(Marker->Location, PlayerPawns) > InteractionRadius)
    {
        return;
    }

    if (ShouldWaitForDefenseHorde(ObjectiveId))
    {
        FName HordeId = DefenseObjectiveHordes.FindRef(ObjectiveId);
        if (HordeId == NAME_None)
        {
            HordeId = FindNearestHordeId(Marker->District, Marker->Location);
            if (HordeId != NAME_None)
            {
                DefenseObjectiveHordes.Add(ObjectiveId, HordeId);
                ActivateHordeInternal(HordeId);
            }
        }

        if (HordeId != NAME_None && !IsHordeCleared(HordeId))
        {
            return;
        }
    }

    CompleteObjective(ObjectiveId);
}

void UZSGameplayRuntimeSubsystem::ProcessExtraction(const TArray<APawn*>& PlayerPawns)
{
    if (!bExtractionReady || bExtractionCompleted)
    {
        return;
    }

    if (DistanceToNearestPlayer(ZombieSeasonsRuntime::ExtractionEndpoint, PlayerPawns) > ZombieSeasonsRuntime::ExtractionEndpointRadius)
    {
        return;
    }

    bExtractionCompleted = true;
    UE_LOG(LogZombieSeasonsRuntime, Display, TEXT("Extraction completed at the frozen dam endpoint."));
    OnExtractionCompleted.Broadcast();
}

bool UZSGameplayRuntimeSubsystem::ActivateHordeInternal(FName HordeId)
{
    if (HordeId == NAME_None || ActivatedHordes.Contains(HordeId))
    {
        return HordeId != NAME_None;
    }

    FMarkerRecord* HordeMarker = FindMarker(HordeId);
    if (!HordeMarker || HordeMarker->Role != TEXT("HordeTrigger"))
    {
        return false;
    }

    const int32 MaxActive = FMath::Max(0, ZombieSeasonsRuntime::CVarMaxActiveEnemies.GetValueOnGameThread());
    const int32 Capacity = FMath::Max(0, MaxActive - GetActiveEnemyCount());
    const int32 TargetBurst = FMath::Min(
        Capacity,
        FMath::Max(0, ZombieSeasonsRuntime::CVarHordeBurstSize.GetValueOnGameThread()));

    struct FHordeCandidate
    {
        int32 MarkerIndex = INDEX_NONE;
        float Distance = 0.0f;
    };

    TArray<FHordeCandidate> Candidates;
    for (int32 Index = 0; Index < Markers.Num(); ++Index)
    {
        const FMarkerRecord& Marker = Markers[Index];
        if (Marker.Role != TEXT("ZombieSpawnCandidate") || Marker.bConsumed || !Marker.Actor.IsValid())
        {
            continue;
        }
        if (Marker.District != HordeMarker->District)
        {
            continue;
        }

        const float Distance = FVector::Dist(Marker.Location, HordeMarker->Location);
        if (Distance <= ZombieSeasonsRuntime::HordeSpawnSearchRadius)
        {
            Candidates.Add({Index, Distance});
        }
    }

    Candidates.Sort([](const FHordeCandidate& Left, const FHordeCandidate& Right)
    {
        if (!FMath::IsNearlyEqual(Left.Distance, Right.Distance))
        {
            return Left.Distance < Right.Distance;
        }
        return Left.MarkerIndex < Right.MarkerIndex;
    });

    int32 Spawned = 0;
    for (const FHordeCandidate& Candidate : Candidates)
    {
        if (Spawned >= TargetBurst)
        {
            break;
        }
        if (Markers.IsValidIndex(Candidate.MarkerIndex) && SpawnEnemyFromMarker(Markers[Candidate.MarkerIndex], HordeId))
        {
            ++Spawned;
        }
    }

    ActivatedHordes.Add(HordeId);
    ActiveHordes.Add(HordeId);

    UE_LOG(
        LogZombieSeasonsRuntime,
        Display,
        TEXT("Horde activated: %s District=%s Spawned=%d ActiveEnemies=%d"),
        *HordeId.ToString(),
        *HordeMarker->District.ToString(),
        Spawned,
        GetActiveEnemyCount());

    return true;
}

bool UZSGameplayRuntimeSubsystem::ForceActivateHorde(FName HordeId)
{
    return ActivateHordeInternal(HordeId);
}

bool UZSGameplayRuntimeSubsystem::SpawnEnemyFromMarker(FMarkerRecord& Marker, FName HordeId)
{
    UWorld* World = GetWorld();
    if (!World || !EnemyClass || Marker.bConsumed || !Marker.Actor.IsValid())
    {
        return false;
    }

    FVector SpawnLocation = Marker.Location;
    ProjectSpawnLocationToNavigation(Marker.Location, SpawnLocation);
    SpawnLocation.Z += 20.0f;

    FTransform SpawnTransform(FRotator::ZeroRotator, SpawnLocation);
    FActorSpawnParameters SpawnParameters;
    SpawnParameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;

    AActor* SpawnedActor = World->SpawnActor(EnemyClass.Get(), &SpawnTransform, SpawnParameters);
    APawn* EnemyPawn = Cast<APawn>(SpawnedActor);
    if (!EnemyPawn)
    {
        if (IsValid(SpawnedActor))
        {
            SpawnedActor->Destroy();
        }
        return false;
    }

    EnemyPawn->Tags.AddUnique(TEXT("ZS.RuntimeSpawned"));
    EnemyPawn->Tags.AddUnique(FName(*FString::Printf(TEXT("ZS.SourceMarker.%s"), *Marker.StableId.ToString())));
    if (HordeId != NAME_None)
    {
        EnemyPawn->Tags.AddUnique(FName(*FString::Printf(TEXT("ZS.RuntimeHorde.%s"), *HordeId.ToString())));
    }

    if (!EnemyPawn->GetController() && EnemyControllerClass)
    {
        FTransform ControllerTransform(EnemyPawn->GetActorRotation(), EnemyPawn->GetActorLocation());
        FActorSpawnParameters ControllerSpawnParameters;
        ControllerSpawnParameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

        AActor* ControllerActor = World->SpawnActor(
            EnemyControllerClass.Get(),
            &ControllerTransform,
            ControllerSpawnParameters);

        if (AAIController* AIController = Cast<AAIController>(ControllerActor))
        {
            AIController->Possess(EnemyPawn);
        }
        else if (IsValid(ControllerActor))
        {
            ControllerActor->Destroy();
        }
    }

    Marker.bConsumed = true;
    FSpawnedEnemyRecord Record;
    Record.Pawn = EnemyPawn;
    Record.SourceMarkerId = Marker.StableId;
    Record.HordeId = HordeId;
    SpawnedEnemies.Add(MoveTemp(Record));
    return true;
}

bool UZSGameplayRuntimeSubsystem::ProjectSpawnLocationToNavigation(
    const FVector& Source,
    FVector& OutLocation) const
{
    UWorld* World = GetWorld();
    if (!World)
    {
        OutLocation = Source;
        return false;
    }

    UNavigationSystemV1* NavigationSystem = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!NavigationSystem)
    {
        OutLocation = Source;
        return false;
    }

    FNavLocation Projected;
    const FVector Extent(
        ZombieSeasonsRuntime::NavigationProjectionExtentXY,
        ZombieSeasonsRuntime::NavigationProjectionExtentXY,
        ZombieSeasonsRuntime::NavigationProjectionExtentZ);

    if (NavigationSystem->ProjectPointToNavigation(Source, Projected, Extent))
    {
        OutLocation = Projected.Location;
        return true;
    }

    OutLocation = Source;
    return false;
}

void UZSGameplayRuntimeSubsystem::ReleaseSourceMarker(FName SourceMarkerId)
{
    if (FMarkerRecord* Marker = FindMarker(SourceMarkerId))
    {
        Marker->bConsumed = false;
    }
}

int32 UZSGameplayRuntimeSubsystem::GetActiveEnemyCount() const
{
    int32 Count = 0;
    for (const FSpawnedEnemyRecord& Record : SpawnedEnemies)
    {
        if (Record.Pawn.IsValid())
        {
            ++Count;
        }
    }
    return Count;
}

FName UZSGameplayRuntimeSubsystem::GetCurrentObjectiveId() const
{
    return ObjectiveSequence.IsValidIndex(CurrentObjectiveIndex)
        ? ObjectiveSequence[CurrentObjectiveIndex]
        : NAME_None;
}

bool UZSGameplayRuntimeSubsystem::CompleteObjective(FName ObjectiveId)
{
    const FName Current = GetCurrentObjectiveId();
    if (ObjectiveId == NAME_None || Current == NAME_None || ObjectiveId != Current)
    {
        return false;
    }

    CompletedObjectives.Add(ObjectiveId);
    OnObjectiveCompleted.Broadcast(ObjectiveId);

    UE_LOG(
        LogZombieSeasonsRuntime,
        Display,
        TEXT("Objective completed [%d/%d]: %s"),
        CurrentObjectiveIndex + 1,
        ObjectiveSequence.Num(),
        *ObjectiveId.ToString());

    ++CurrentObjectiveIndex;

    const FName NextObjective = GetCurrentObjectiveId();
    if (NextObjective != NAME_None)
    {
        OnObjectiveChanged.Broadcast(NextObjective, CurrentObjectiveIndex);
    }
    else if (!bExtractionReady)
    {
        bExtractionReady = true;
        UE_LOG(LogZombieSeasonsRuntime, Display, TEXT("All canonical objectives complete. Extraction endpoint is now active."));
        OnExtractionReady.Broadcast();
    }

    return true;
}

UZSGameplayRuntimeSubsystem::FMarkerRecord* UZSGameplayRuntimeSubsystem::FindMarker(FName StableId)
{
    if (const int32* Index = MarkerIndexById.Find(StableId))
    {
        return Markers.IsValidIndex(*Index) ? &Markers[*Index] : nullptr;
    }
    return nullptr;
}

const UZSGameplayRuntimeSubsystem::FMarkerRecord* UZSGameplayRuntimeSubsystem::FindMarker(FName StableId) const
{
    if (const int32* Index = MarkerIndexById.Find(StableId))
    {
        return Markers.IsValidIndex(*Index) ? &Markers[*Index] : nullptr;
    }
    return nullptr;
}

FName UZSGameplayRuntimeSubsystem::FindNearestHordeId(FName District, const FVector& Origin) const
{
    float BestDistance = TNumericLimits<float>::Max();
    FName BestId = NAME_None;

    for (const FMarkerRecord& Marker : Markers)
    {
        if (Marker.Role != TEXT("HordeTrigger") || Marker.District != District)
        {
            continue;
        }

        const float Distance = FVector::DistSquared(Origin, Marker.Location);
        if (Distance < BestDistance)
        {
            BestDistance = Distance;
            BestId = Marker.StableId;
        }
    }

    return BestId;
}

bool UZSGameplayRuntimeSubsystem::IsHordeCleared(FName HordeId) const
{
    if (HordeId == NAME_None)
    {
        return true;
    }

    for (const FSpawnedEnemyRecord& Record : SpawnedEnemies)
    {
        if (Record.HordeId == HordeId && Record.Pawn.IsValid())
        {
            return false;
        }
    }
    return true;
}

bool UZSGameplayRuntimeSubsystem::ShouldWaitForDefenseHorde(FName ObjectiveId) const
{
    const FString Id = ObjectiveId.ToString();
    return Id == TEXT("Autumn.Objective.PoliceDefenseComplete")
        || Id == TEXT("Extraction.Objective.DefenseA")
        || Id == TEXT("Extraction.Objective.DefenseB");
}

bool UZSGameplayRuntimeSubsystem::ExtractPrefixedTag(
    const AActor* Actor,
    const FString& Prefix,
    FName& OutValue)
{
    if (!Actor)
    {
        return false;
    }

    for (const FName Tag : Actor->Tags)
    {
        const FString TagString = Tag.ToString();
        if (TagString.StartsWith(Prefix, ESearchCase::CaseSensitive))
        {
            OutValue = FName(*TagString.Mid(Prefix.Len()));
            return true;
        }
    }
    return false;
}

bool UZSGameplayRuntimeSubsystem::ActorHasExactTag(const AActor* Actor, const FName Tag)
{
    return Actor && Actor->Tags.Contains(Tag);
}

class FZombieSeasonsRuntimeModule final : public IModuleInterface
{
};

IMPLEMENT_MODULE(FZombieSeasonsRuntimeModule, ZombieSeasonsRuntime)
