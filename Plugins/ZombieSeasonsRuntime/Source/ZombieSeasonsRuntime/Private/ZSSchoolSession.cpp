#include "ZSSchoolScenario.h"
#include "ZSSchoolOverlay.h"
#include "ZSSchoolHUDModel.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"

void AZSSchoolScenario::SetEnemyAwake(APawn* Enemy, bool bAwake)
{
    ACharacter* Character = Cast<ACharacter>(Enemy);
    if (!IsValid(Character) || FZSSchoolHUDModel::IsDead(Character)) { return; }
    if (bAwake) { Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking); }
    else { Character->GetCharacterMovement()->DisableMovement(); }
    if (AAIController* AI = Cast<AAIController>(Character->GetController()))
    {
        if (!bAwake) { AI->StopMovement(); }
        if (UBrainComponent* Brain = AI->GetBrainComponent())
        {
            if (bAwake) { Brain->RestartLogic(); }
            else { Brain->StopLogic(TEXT("School encounter not started")); }
        }
    }
}

void AZSSchoolScenario::InitializeSession()
{
    for (APawn* Enemy : EntryEnemies) { SetEnemyAwake(Enemy, false); TrackedEnemies.Add(Enemy); }
    for (APawn* Enemy : WaitingEnemies) { TrackedEnemies.Add(Enemy); }
}

void AZSSchoolScenario::CreateOverlay(APlayerController* PC)
{
    // Remove only the legacy HUD from this map, retaining its Blueprint reference for old update calls.
    TArray<UUserWidget*> Widgets;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this, Widgets, UUserWidget::StaticClass(), false);
    for (UUserWidget* Widget : Widgets)
    {
        if (Widget->GetClass()->GetFName() == TEXT("WBP_InGameHUD_C")) { Widget->RemoveFromParent(); }
    }
    Overlay = CreateWidget<UZSSchoolOverlay>(PC);
    if (!Overlay) { return; }
    Overlay->SetIsFocusable(true);
    Overlay->AddToViewport(20);
    Overlay->OnPrimary = [this]
    {
        if (Overlay->Screen == 1) { StartSession(); }
        else if (Overlay->Screen == 4) { SetScreen(0); }
        else { ReloadSession(true); }
    };
    Overlay->OnMenu = [this] { ReloadSession(false); };
    if (bSmokeMode || GetWorld()->URL.HasOption(TEXT("SchoolQuickStart"))) { StartSession(); }
    else { SetScreen(1); }
}

void AZSSchoolScenario::SetScreen(int32 Screen)
{
    if (!Overlay) { return; }
    Overlay->Screen = Screen;
    APlayerController* PC = GetWorld()->GetFirstPlayerController();
    if (!PC) { return; }
    const bool bMenu = Screen != 0;
    Overlay->SetVisibility(bMenu ? ESlateVisibility::Visible : ESlateVisibility::HitTestInvisible);
    PC->bShowMouseCursor = bMenu;
    if (bMenu)
    {
        FInputModeUIOnly Mode;
        Mode.SetWidgetToFocus(Overlay->TakeWidget());
        PC->SetInputMode(Mode);
    }
    else { PC->SetInputMode(FInputModeGameOnly()); }
    // The automated capture sequence must continue ticking through menu previews.
    if (!bSmokeMode) { UGameplayStatics::SetGamePaused(this, bMenu); }
}

void AZSSchoolScenario::StartSession()
{
    bRunStarted = true;
    StartedAt = GetWorld()->GetTimeSeconds();
    SetScreen(0);
}

void AZSSchoolScenario::ReloadSession(bool bQuickStart)
{
    UGameplayStatics::SetGamePaused(this, false);
    UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, bQuickStart ? TEXT("SchoolQuickStart") : TEXT(""));
}

void AZSSchoolScenario::UpdateSession(APlayerController* PC)
{
    if (!Overlay || !bRunStarted) { return; }
    Overlay->bHealthKnown = FZSSchoolHUDModel::ReadHealth(PC->GetPawn(), Overlay->Health, Overlay->MaximumHealth);
    Overlay->Health = FMath::Max(0.f, Overlay->Health);
    if (Overlay->Screen != 0) { return; }
    Overlay->Elapsed = GetWorld()->GetTimeSeconds() - StartedAt;
    Overlay->bPrepared = Progress.bPreparationOpen;
    for (const TWeakObjectPtr<APawn>& Enemy : TrackedEnemies)
    {
        if (Enemy.IsValid() && !CountedEnemies.Contains(Enemy) && FZSSchoolHUDModel::IsDead(Enemy.Get()))
        {
            CountedEnemies.Add(Enemy);
            ++Overlay->Kills;
        }
    }
    Overlay->Score = FZSSchoolHUDModel::ScoreForKills(Overlay->Kills);
    if (!bSmokeMode && FZSSchoolHUDModel::IsDead(PC->GetPawn())) { SetScreen(3); return; }
    // The courtyard remains safe: time alone cannot unleash enemies at the spawn.
    if (!bEntryAwake && Overlay->Elapsed >= 12.f && PC->GetPawn()->GetActorLocation().X > -1650.f)
    {
        bEntryAwake = true;
        for (APawn* Enemy : EntryEnemies) { SetEnemyAwake(Enemy, true); }
    }
}
