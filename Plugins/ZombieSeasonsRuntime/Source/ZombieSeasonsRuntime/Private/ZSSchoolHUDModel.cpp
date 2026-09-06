#include "ZSSchoolHUDModel.h"
#include "UObject/UnrealType.h"

namespace
{
    bool Number(const UObject* Object, FName Name, float& Value)
    {
        if (!IsValid(Object)) { return false; }
        const FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        if (!Property) { return false; }
        const void* Address = Property->ContainerPtrToValuePtr<void>(Object);
        Value = Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Address) : Property->GetSignedIntPropertyValue(Address);
        return FMath::IsFinite(Value);
    }
}

bool FZSSchoolHUDModel::ReadHealth(const UObject* Actor, float& Current, float& Maximum)
{
    return Number(Actor, TEXT("HealthPoints"), Current) && Number(Actor, TEXT("HealthPointsMax"), Maximum) && Maximum > 0;
}

bool FZSSchoolHUDModel::IsDead(const UObject* Actor)
{
    if (!IsValid(Actor)) { return false; }
    if (const FBoolProperty* Dead = FindFProperty<FBoolProperty>(Actor->GetClass(), TEXT("IsDead")))
    {
        if (Dead->GetPropertyValue_InContainer(Actor)) { return true; }
    }
    float Health = 0, Max = 0;
    return ReadHealth(Actor, Health, Max) && Health <= 0;
}
