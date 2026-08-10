#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ZSGameplayRuntimeSubsystem.generated.h"

class AActor;
class AAIController;
class APawn;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FZSObjectiveChangedSignature, FName, ObjectiveId, int32, ObjectiveIndex);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FZSObjectiveCompletedSignature, FName, ObjectiveId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FZSExtractionReadySignature);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FZSExtractionCompletedSignature);

/**
 * Runtime bridge between deterministic Stage 9B marker actors and the existing
 * Blueprint gameplay classes. The subsystem is auto-created for game worlds and
 * requires no Blueprint wiring to start operating.
 */
UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSGameplayRuntimeSubsystem final : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintPure, Category = "ZombieSeasons|Runtime")
    FName GetCurrentObjectiveId() const;

    UFUNCTION(BlueprintCallable, Category = "ZombieSeasons|Runtime")
    bool CompleteObjective(FName ObjectiveId);

    UFUNCTION(BlueprintCallable, Category = "ZombieSeasons|Runtime")
    bool ForceActivateHorde(FName HordeId);

    UFUNCTION(BlueprintPure, Category = "ZombieSeasons|Runtime")
    int32 GetActiveEnemyCount() const;

    UFUNCTION(BlueprintPure, Category = "ZombieSeasons|Runtime")
    bool IsExtractionReady() const { return bExtractionReady; }

    UFUNCTION(BlueprintPure, Category = "ZombieSeasons|Runtime")
    bool IsExtractionCompleted() const { return bExtractionCompleted; }

    UPROPERTY(BlueprintAssignable, Category = "ZombieSeasons|Runtime")
    FZSObjectiveChangedSignature OnObjectiveChanged;

    UPROPERTY(BlueprintAssignable, Category = "ZombieSeasons|Runtime")
    FZSObjectiveCompletedSignature OnObjectiveCompleted;

    UPROPERTY(BlueprintAssignable, Category = "ZombieSeasons|Runtime")
    FZSExtractionReadySignature OnExtractionReady;

    UPROPERTY(BlueprintAssignable, Category = "ZombieSeasons|Runtime")
    FZSExtractionCompletedSignature OnExtractionCompleted;

private:
    struct FMarkerRecord
    {
        TWeakObjectPtr<AActor> Actor;
        FName StableId = NAME_None;
        FName District = NAME_None;
        FName Role = NAME_None;
        FName SpawnGroup = NAME_None;
        FVector Location = FVector::ZeroVector;
        bool bConsumed = false;
    };

    struct FSpawnedEnemyRecord
    {
        TWeakObjectPtr<APawn> Pawn;
        FName SourceMarkerId = NAME_None;
        FName HordeId = NAME_None;
    };

    void RuntimePulse();
    void ScanGameplayMarkers();
    void LoadGameplayClasses();
    void InitializeObjectiveSequence();

    void PruneAndDespawnEnemies(const TArray<APawn*>& PlayerPawns);
    void ProcessAutomaticHordeTriggers(const TArray<APawn*>& PlayerPawns);
    void ProcessAmbientSpawning(const TArray<APawn*>& PlayerPawns);
    void ProcessCurrentObjective(const TArray<APawn*>& PlayerPawns);
    void ProcessExtraction(const TArray<APawn*>& PlayerPawns);

    bool ActivateHordeInternal(FName HordeId);
    bool SpawnEnemyFromMarker(FMarkerRecord& Marker, FName HordeId = NAME_None);
    bool ProjectSpawnLocationToNavigation(const FVector& Source, FVector& OutLocation) const;
    void ReleaseSourceMarker(FName SourceMarkerId);

    FMarkerRecord* FindMarker(FName StableId);
    const FMarkerRecord* FindMarker(FName StableId) const;
    FName FindNearestHordeId(FName District, const FVector& Origin) const;
    bool IsHordeCleared(FName HordeId) const;
    bool ShouldWaitForDefenseHorde(FName ObjectiveId) const;

    TArray<APawn*> GatherPlayerPawns() const;
    float DistanceToNearestPlayer(const FVector& Location, const TArray<APawn*>& PlayerPawns) const;

    static bool ExtractPrefixedTag(const AActor* Actor, const FString& Prefix, FName& OutValue);
    static bool ActorHasExactTag(const AActor* Actor, const FName Tag);

    TArray<FMarkerRecord> Markers;
    TMap<FName, int32> MarkerIndexById;
    TArray<FSpawnedEnemyRecord> SpawnedEnemies;
    TSet<FName> ActivatedHordes;
    TSet<FName> ActiveHordes;
    TSet<FName> CompletedObjectives;
    TMap<FName, FName> DefenseObjectiveHordes;
    TArray<FName> ObjectiveSequence;

    TSubclassOf<APawn> EnemyClass;
    TSubclassOf<AAIController> EnemyControllerClass;

    FTimerHandle RuntimeTimerHandle;
    int32 CurrentObjectiveIndex = 0;
    float SafeZoneRadiusCm = 6000.0f;
    bool bExtractionReady = false;
    bool bExtractionCompleted = false;
};
