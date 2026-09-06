#include "ZSSchoolProgress.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FZSSchoolProgressTest, "ZombieSeasons.School.Progression", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FZSSchoolProgressTest::RunTest(const FString& Parameters)
{
    FZSSchoolProgress State;
    TestFalse(TEXT("Cannot activate before connection"), State.Activate());
    TestFalse(TEXT("Cannot finish early"), State.Complete());
    TestFalse(TEXT("Shortcut not unlocked before incident"), State.OpenShortcut());
    TestTrue(TEXT("Preparation is independent"), State.OpenPreparation());
    TestFalse(TEXT("Preparation reward once"), State.OpenPreparation());
    TestTrue(TEXT("First connection"), State.Connect());
    TestFalse(TEXT("Double connection refused"), State.Connect());
    TestTrue(TEXT("Remote command activates"), State.Activate());
    TestFalse(TEXT("Repeated remote command refused"), State.Activate());
    TestFalse(TEXT("No completion before return route"), State.Complete());
    TestTrue(TEXT("Shortcut does not require kills"), State.OpenShortcut());
    TestFalse(TEXT("Shortcut once"), State.OpenShortcut());
    TestTrue(TEXT("Completion without kill count"), State.Complete());
    TestFalse(TEXT("Completion once"), State.Complete());
    TestFalse(TEXT("Cannot reconnect completed scenario"), State.Connect());
    FZSSchoolProgress WithoutPreparation;
    WithoutPreparation.Connect(); WithoutPreparation.Activate(); WithoutPreparation.OpenShortcut();
    TestTrue(TEXT("Optional passage never required"), WithoutPreparation.Complete());
    return true;
}
#endif
