#pragma once

#include "CoreMinimal.h"

/** Reads the existing Blueprint combat state; never creates a second health system. */
struct FZSSchoolHUDModel
{
    static bool ReadHealth(const UObject* Actor, float& Current, float& Maximum);
    static bool IsDead(const UObject* Actor);
    static int32 ScoreForKills(int32 Kills) { return FMath::Max(0, Kills) * 100; }
};
