#pragma once

#include "CoreMinimal.h"

/** Local A1 progression. Enemy kills never gate the exit. */
struct FZSSchoolProgress
{
    enum class EPhase : uint8 { Offline, Connected, Active, Complete };
    EPhase Phase = EPhase::Offline;
    bool bPreparationOpen = false;
    bool bShortcutOpen = false;

    bool Connect()
    {
        if (Phase != EPhase::Offline) { return false; }
        Phase = EPhase::Connected;
        return true;
    }
    bool Activate()
    {
        if (Phase != EPhase::Connected) { return false; }
        Phase = EPhase::Active;
        return true;
    }
    bool OpenPreparation()
    {
        if (bPreparationOpen) { return false; }
        bPreparationOpen = true;
        return true;
    }
    bool OpenShortcut()
    {
        if (bShortcutOpen || Phase != EPhase::Active) { return false; }
        bShortcutOpen = true;
        return true;
    }
    bool Complete()
    {
        if (Phase != EPhase::Active || !bShortcutOpen) { return false; }
        Phase = EPhase::Complete;
        return true;
    }
};
