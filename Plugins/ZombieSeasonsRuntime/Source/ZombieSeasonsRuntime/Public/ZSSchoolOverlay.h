#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ZSSchoolOverlay.generated.h"

UCLASS()
class ZOMBIESEASONSRUNTIME_API UZSSchoolOverlay final : public UUserWidget
{
    GENERATED_BODY()
public:
    FText Objective, Status, Interaction;
    float Health = 100, MaximumHealth = 100;
    bool bHealthKnown = false;
    int32 Score = 0, Kills = 0;
    float Elapsed = 0;
    bool bPrepared = false;
    // 0: play, 1: welcome, 2: success, 3: death, 4: pause.
    int32 Screen = 1;
    TFunction<void()> OnPrimary, OnRestart, OnMenu;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
};
