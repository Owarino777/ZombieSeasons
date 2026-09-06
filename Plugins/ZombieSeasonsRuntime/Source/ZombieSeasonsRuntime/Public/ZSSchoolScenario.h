#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ZSSchoolProgress.h"
#include "ZSSchoolScenario.generated.h"

class APawn;
class UZSSchoolOverlay;

/** Explicit, map-local school scenario. Does not alter player or weapon classes. */
UCLASS()
class ZOMBIESEASONSRUNTIME_API AZSSchoolScenario final : public AActor
{
    GENERATED_BODY()
public:
    AZSSchoolScenario();
    virtual void Tick(float DeltaSeconds) override;

    UPROPERTY(EditInstanceOnly, Category="School") TObjectPtr<AActor> Relay;
    UPROPERTY(EditInstanceOnly, Category="School") TObjectPtr<AActor> PreparationControl;
    UPROPERTY(EditInstanceOnly, Category="School") TObjectPtr<AActor> PreparationDoor;
    UPROPERTY(EditInstanceOnly, Category="School") TObjectPtr<AActor> ShortcutControl;
    UPROPERTY(EditInstanceOnly, Category="School") TObjectPtr<AActor> ShortcutDoor;
    UPROPERTY(EditInstanceOnly, Category="School") TObjectPtr<AActor> ReturnPoint;
    UPROPERTY(EditInstanceOnly, Category="School") TArray<TObjectPtr<APawn>> EntryEnemies;
    UPROPERTY(EditInstanceOnly, Category="School") TArray<TObjectPtr<APawn>> WaitingEnemies;
    UPROPERTY(EditInstanceOnly, Category="School") TArray<TObjectPtr<AActor>> IncidentLights;
    UPROPERTY(EditInstanceOnly, Category="School") TArray<FVector> TestRoute;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    void InitializeSession();
    void CreateOverlay(APlayerController* PC);
    void SetScreen(int32 Screen);
    void StartSession();
    void ReloadSession(bool bQuickStart);
    void UpdateSession(APlayerController* PC);
    void SetEnemyAwake(APawn* Enemy, bool bAwake);
    bool CanInteract(const AActor* Target) const;
    void Interact();
    void ActivateSector();
    void UpdateOverlay();
    void RunSmokeStep();
    void FinishSmoke();
    void SetDoorOpen(AActor* Door);

    UPROPERTY(Transient) TObjectPtr<UZSSchoolOverlay> Overlay;
    FZSSchoolProgress Progress;
    TArray<TWeakObjectPtr<APawn>> TrackedEnemies;
    TSet<TWeakObjectPtr<APawn>> CountedEnemies;
    bool bRunStarted = false;
    bool bEntryAwake = false;
    FTimerHandle ActivationTimer;
    FTimerHandle SmokeTimer;
    FTimerHandle CaptureTimer;
    float StartedAt = 0;
    float ActivatedAt = 0;
    float CompletedAt = 0;
    int32 SmokeStep = 0;
    bool bSmokeMode = false;
    bool bSmokeNavigationPassed = false;
    bool bSmokeStatePassed = false;
};
