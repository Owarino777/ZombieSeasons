#include "ZSSchoolScenario.h"
#include "ZSSchoolOverlay.h"
#include "ZSSchoolHUDModel.h"
#include "UObject/StructOnScope.h"
#include "UObject/UnrealType.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Camera/CameraActor.h"
#include "Components/LightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "UnrealClient.h"

#define LOCTEXT_NAMESPACE "ZombieSeasonsSchool"
DEFINE_LOG_CATEGORY_STATIC(LogZSSchool, Log, All);

AZSSchoolScenario::AZSSchoolScenario()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AZSSchoolScenario::BeginPlay()
{
    Super::BeginPlay();
    StartedAt = GetWorld()->GetTimeSeconds();
    // The generated A1 has no baked navigation tiles; build its compact bounds at startup.
    if (UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld())) { Navigation->Build(); }
    bSmokeMode = FParse::Param(FCommandLine::Get(), TEXT("ZSSchoolSmoke"));
    IFileManager::Get().MakeDirectory(*(FPaths::ProjectSavedDir() / TEXT("SchoolA1")), true);
    if (!Relay || !PreparationControl || !PreparationDoor || !ShortcutControl || !ShortcutDoor || !ReturnPoint)
    {
        UE_LOG(LogZSSchool, Error, TEXT("School scenario has missing references; refusing initialization."));
        SetActorTickEnabled(false);
        return;
    }
    for (APawn* Enemy : WaitingEnemies)
    {
        if (ACharacter* Character = Cast<ACharacter>(Enemy))
        {
            Character->GetCharacterMovement()->DisableMovement();
            if (AAIController* AI = Cast<AAIController>(Character->GetController()))
            {
                AI->StopMovement();
                if (AI->GetBrainComponent()) { AI->GetBrainComponent()->StopLogic(TEXT("Waiting in school B")); }
            }
        }
    }
    InitializeSession();
    if (bSmokeMode)
    {
        GetWorldTimerManager().SetTimer(SmokeTimer, this, &AZSSchoolScenario::RunSmokeStep, 5.0f, true);
    }
    UE_LOG(LogZSSchool, Display, TEXT("School A1 initialized. Waiting enemies=%d. No legacy objectives."), WaitingEnemies.Num());
}

void AZSSchoolScenario::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(ActivationTimer);
    GetWorldTimerManager().ClearTimer(SmokeTimer);
    GetWorldTimerManager().ClearTimer(CaptureTimer);
    if (Overlay) { Overlay->RemoveFromParent(); Overlay = nullptr; }
    Super::EndPlay(Reason);
}

bool AZSSchoolScenario::CanInteract(const AActor* Target) const
{
    APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (!IsValid(Target) || !PC || !PC->GetPawn()) { return false; }
    FVector Eye; FRotator View;
    PC->GetPlayerViewPoint(Eye, View);
    const FVector Offset = Target->GetActorLocation() - Eye;
    if (Offset.SizeSquared() > FMath::Square(260.0f) || FVector::DotProduct(View.Vector(), Offset.GetSafeNormal()) < 0.4f) { return false; }
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(SchoolInteraction), false, PC->GetPawn());
    const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, Eye, Target->GetActorLocation(), ECC_Visibility, Params);
    return !bHit || Hit.GetActor() == Target;
}

void AZSSchoolScenario::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (!PC || !PC->IsLocalController() || !PC->GetPawn()) { return; }
    if (!Overlay) { CreateOverlay(PC); }
    if (!Overlay) { return; }
    UpdateSession(PC);
    if (Overlay->Screen != 0) { return; }
    if (PC->WasInputKeyJustPressed(EKeys::Escape)) { SetScreen(4); return; }
    if (PC->WasInputKeyJustPressed(EKeys::E)) { Interact(); }
    UpdateOverlay();
}

void AZSSchoolScenario::SetDoorOpen(AActor* Door)
{
    if (!IsValid(Door)) { return; }
    // The A1 leaf is stowed above the lintel; the final art pass replaces this motion.
    Door->SetActorEnableCollision(false);
    Door->SetActorLocation(Door->GetActorLocation() + FVector(0, 0, 450));
}

void AZSSchoolScenario::Interact()
{
    if (!Progress.bPreparationOpen && CanInteract(PreparationControl))
    {
        if (Progress.OpenPreparation()) { SetDoorOpen(PreparationDoor); }
    }
    else if (CanInteract(Relay) && Progress.Connect())
    {
        UE_LOG(LogZSSchool, Display, TEXT("LINK_RESTORED: waiting for remote command."));
        GetWorldTimerManager().SetTimer(ActivationTimer, this, &AZSSchoolScenario::ActivateSector, 3.0f, false);
    }
    else if (CanInteract(ShortcutControl) && Progress.OpenShortcut())
    {
        SetDoorOpen(ShortcutDoor);
        UE_LOG(LogZSSchool, Display, TEXT("SHORTCUT_OPEN: no kill requirement."));
    }
    else if (CanInteract(ReturnPoint) && Progress.Complete())
    {
        CompletedAt = GetWorld()->GetTimeSeconds();
        SetScreen(2);
        UE_LOG(LogZSSchool, Display, TEXT("A1_RUN_COMPLETE elapsed=%.2fs. Human review and full expedition still required."), CompletedAt - StartedAt);
    }
}

void AZSSchoolScenario::ActivateSector()
{
    if (!Progress.Activate()) { return; }
    ActivatedAt = GetWorld()->GetTimeSeconds();
    for (AActor* LightActor : IncidentLights)
    {
        if (!IsValid(LightActor)) { continue; }
        TArray<ULightComponent*> Lights;
        LightActor->GetComponents(Lights);
        for (ULightComponent* Light : Lights) { Light->SetVisibility(true); }
    }
    for (APawn* Enemy : WaitingEnemies)
    {
        ACharacter* Character = Cast<ACharacter>(Enemy);
        // Existing death handling may disable collision before destroying the pawn.
        if (!IsValid(Character) || Character->IsActorBeingDestroyed() || !Character->GetActorEnableCollision()) { continue; }
        Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        if (!Character->GetController()) { Character->SpawnDefaultController(); }
        if (AAIController* AI = Cast<AAIController>(Character->GetController()))
        {
            if (AI->GetBrainComponent()) { AI->GetBrainComponent()->RestartLogic(); }
        }
    }
    UE_LOG(LogZSSchool, Display, TEXT("REMOTE_COMMAND_RECEIVED / B_ACTIVE (single activation)."));
}

void AZSSchoolScenario::UpdateOverlay()
{

    if (!Overlay) { return; }
    using EPhase = FZSSchoolProgress::EPhase;
    Overlay->Interaction = FText::GetEmpty();
    if (Progress.Phase == EPhase::Offline)
    {
        Overlay->Objective = LOCTEXT("RelayObjective", "Retrouvez la radio");
        Overlay->Status = LOCTEXT("Offline", "Entrez par la cuisine. Le bureau d’accueil est au bout du couloir.");
        if (CanInteract(Relay)) { Overlay->Interaction = LOCTEXT("Connect", "[E] Allumer la radio"); }
    }
    else if (Progress.Phase == EPhase::Connected)
    {
        Overlay->Objective = LOCTEXT("Connection", "Attendez une réponse…");
        Overlay->Status = LOCTEXT("Radio", "Radio : « Poste école ? Vous m'entendez ? »");
    }
    else if (Progress.Phase == EPhase::Active)
    {
        Overlay->Objective = Progress.bShortcutOpen
            ? LOCTEXT("Return", "Rejoignez la cour de livraison")
            : LOCTEXT("Leave", "Sortez par le gymnase");
        Overlay->Status = GetWorld()->GetTimeSeconds() - ActivatedAt < 12
            ? LOCTEXT("Announcement", "Haut-parleur : « Groupe B, préparez-vous au départ. »")
            : LOCTEXT("NoKills", "La porte de service donne sur la cour. Restez en mouvement.");
        if (!Progress.bShortcutOpen && CanInteract(ShortcutControl)) { Overlay->Interaction = LOCTEXT("Shortcut", "[E] Ouvrir le portail de service"); }
        if (Progress.bShortcutOpen && CanInteract(ReturnPoint)) { Overlay->Interaction = LOCTEXT("End", "[E] Signaler votre retour"); }
    }
    else
    {
        Overlay->Objective = LOCTEXT("Finished", "PARCOURS A1 TERMINÉ");
        Overlay->Status = FText::Format(LOCTEXT("Time", "Durée de ce parcours : {0} s. Prototype sans sauvegarde de campagne."), FText::AsNumber(FMath::RoundToInt(CompletedAt - StartedAt)));
    }
    if (!Progress.bPreparationOpen && CanInteract(PreparationControl)) { Overlay->Interaction = LOCTEXT("Prepare", "[E] Déverrouiller la porte de service"); }
}

void AZSSchoolScenario::RunSmokeStep()
{
    ++SmokeStep;
    APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (!PC || !PC->GetPawn()) { FinishSmoke(); return; }
    PC->GetPawn()->SetCanBeDamaged(false); // Automated capture only; ordinary play is unchanged.
    if (SmokeStep == 1) { SetScreen(1); }
    if (SmokeStep == 3)
    {
        if (Overlay) { Overlay->SetVisibility(ESlateVisibility::Hidden); }
        for (TActorIterator<AActor> It(GetWorld()); It; ++It)
        {
            if (It->ActorHasTag(TEXT("ZS.School.Roof"))) { It->SetActorHiddenInGame(true); }
        }
    }
    const FString CameraTag = SmokeStep == 1 ? TEXT("ZS.School.Camera.Before") : SmokeStep == 2 ? TEXT("ZS.School.Camera.After") : TEXT("ZS.School.Camera.Routes");
    for (TActorIterator<ACameraActor> It(GetWorld()); It; ++It)
    {
        if (It->ActorHasTag(FName(*CameraTag))) { PC->SetViewTarget(*It); break; }
    }
    if (SmokeStep == 2)
    {
        if (Overlay && Overlay->OnPrimary) { Overlay->OnPrimary(); }
        bSmokeStatePassed = Progress.Connect() && !Progress.Connect();
        ActivateSector();
        bSmokeStatePassed &= Progress.Phase == FZSSchoolProgress::EPhase::Active;
        bSmokeStatePassed &= !Progress.Activate();
        Progress.OpenPreparation(); SetDoorOpen(PreparationDoor);
        Progress.OpenShortcut(); SetDoorOpen(ShortcutDoor);
    }
    if (SmokeStep == 3)
    {
        UE_LOG(LogZSSchool, Display, TEXT("NAV_BUILDING %d"), UNavigationSystemV1::IsNavigationBeingBuiltOrLocked(GetWorld()));
        for (const FVector& Point : TestRoute)
        {
            FVector Projected;
            const bool bProjected = UNavigationSystemV1::K2_ProjectPointToNavigation(GetWorld(), Point, Projected, nullptr, nullptr, FVector(100,100,250));
            UE_LOG(LogZSSchool, Display, TEXT("NAV_POINT %s projected=%d result=%s"), *Point.ToString(), bProjected, *Projected.ToString());
        }
        bSmokeNavigationPassed = TestRoute.Num() >= 2;
        for (int32 Index = 1; Index < TestRoute.Num(); ++Index)
        {
            UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(), TestRoute[Index - 1], TestRoute[Index], PC->GetPawn());
            const bool bValid = Path && Path->IsValid() && !Path->IsPartial();
            bSmokeNavigationPassed &= bValid;
            UE_LOG(LogZSSchool, Display, TEXT("SMOKE_PATH %d valid=%d partial=%d points=%d"), Index, bValid, Path ? Path->IsPartial() : -1, Path ? Path->PathPoints.Num() : 0);
        }
    }
    if (SmokeStep == 4)
    {
        SetScreen(0);
        PC->SetViewTarget(PC->GetPawn());
        for (const TWeakObjectPtr<APawn>& Enemy : TrackedEnemies)
        {
            if (Enemy.IsValid()) { SetEnemyAwake(Enemy.Get(), false); Enemy->SetActorEnableCollision(false); }
        }
        auto Affect = [](UObject* Target, double DeltaValue)
        {
            if (!IsValid(Target)) { return false; }
            UFunction* Function = Target->FindFunction(TEXT("AffectHealth"));
            if (!Function) { return false; }
            FNumericProperty* Delta = FindFProperty<FNumericProperty>(Function, TEXT("Delta"));
            if (!Delta || !Delta->IsFloatingPoint()) { return false; }
            FStructOnScope Params(Function);
            Delta->SetFloatingPointPropertyValue(Delta->ContainerPtrToValuePtr<void>(Params.GetStructMemory()), DeltaValue);
            Target->ProcessEvent(Function, Params.GetStructMemory());
            return true;
        };
        float Before = 0, Maximum = 0;
        const bool ReadBefore = FZSSchoolHUDModel::ReadHealth(PC->GetPawn(), Before, Maximum);
        const int32 BeforeKills = Overlay ? Overlay->Kills : 0;
        const bool Damaged = Affect(PC->GetPawn(), -35.0);
        const bool Killed = EntryEnemies.Num() > 0 && Affect(EntryEnemies[0], -1000.0);
        UpdateSession(PC);
        const bool Valid = ReadBefore && Damaged && Killed && Overlay && Overlay->bHealthKnown
            && FMath::IsNearlyEqual(Overlay->Health, FMath::Max(0.f, Before - 35.f))
            && Overlay->Kills == BeforeKills + 1 && Overlay->Score == Overlay->Kills * 100;
        bSmokeStatePassed &= Valid;
        UE_LOG(LogZSSchool, Display, TEXT("SMOKE_LIVE_HEALTH_SCORE passed=%d health=%.1f kills=%d"), Valid, Overlay ? Overlay->Health : -1.f, Overlay ? Overlay->Kills : -1);
    }
    if (SmokeStep == 5) { SetScreen(2); }
    if (SmokeStep <= 5)
    {
        // Let exposure and camera history settle before recording a changed view.
        const int32 CaptureStep = SmokeStep;
        GetWorldTimerManager().SetTimer(CaptureTimer, FTimerDelegate::CreateWeakLambda(this, [CaptureStep]()
        {
            FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / FString::Printf(TEXT("SchoolA1/scene_%d.png"), CaptureStep), CaptureStep != 3, false);
        }), 1.5f, false);
    }
    else { FinishSmoke(); }
}

void AZSSchoolScenario::FinishSmoke()
{
    GetWorldTimerManager().ClearTimer(SmokeTimer);
    const FString Report = FString::Printf(TEXT("{\"mode\":\"automated_smoke_not_human_playthrough\",\"state_pass\":%s,\"nav_pass\":%s,\"elapsed_seconds\":%.2f,\"human_run_duration\":null}"), bSmokeStatePassed ? TEXT("true") : TEXT("false"), bSmokeNavigationPassed ? TEXT("true") : TEXT("false"), GetWorld()->GetTimeSeconds() - StartedAt);
    FFileHelper::SaveStringToFile(Report, *(FPaths::ProjectSavedDir() / TEXT("SchoolA1/smoke.json")));
    UE_LOG(LogZSSchool, Display, TEXT("SCHOOL_SMOKE %s"), *Report);
    UKismetSystemLibrary::QuitGame(this, GetWorld()->GetFirstPlayerController(), EQuitPreference::Quit, true);
}

#undef LOCTEXT_NAMESPACE
