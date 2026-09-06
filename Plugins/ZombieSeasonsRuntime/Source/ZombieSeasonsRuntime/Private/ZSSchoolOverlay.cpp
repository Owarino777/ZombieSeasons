#include "ZSSchoolOverlay.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

#define LOCTEXT_NAMESPACE "SchoolHUD"
TSharedRef<SWidget> UZSSchoolOverlay::RebuildWidget()
{
    const FLinearColor Ink(0.016f, 0.022f, 0.025f, 0.96f);
    const FLinearColor Paper(0.91f, 0.90f, 0.84f);
    const FLinearColor Amber(0.88f, 0.60f, 0.24f);
    const FSlateBrush* Solid = FCoreStyle::Get().GetBrush("WhiteBrush");
    auto Font = [](int32 Size, bool Bold = false) { return FCoreStyle::GetDefaultFontStyle(Bold ? "Bold" : "Regular", Size); };
    return SNew(SOverlay)
    + SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(32, 30)
    [SNew(SBox).WidthOverride(440).Visibility_Lambda([this]{ return Screen == 0 ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed; })
        [SNew(SBorder).BorderImage(Solid).BorderBackgroundColor(Ink).Padding(18)
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Font(Font(11,true)).ColorAndOpacity(Amber).Text(LOCTEXT("Sector", "ÉCOLE MUNICIPALE  /  SECTEUR B"))]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Font(Font(18,true)).ColorAndOpacity(Paper).WrapTextAt(400).Text_Lambda([this]{return Objective;})]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Font(Font(14)).ColorAndOpacity(Paper).WrapTextAt(400).Text_Lambda([this]{return Status;})]
            ]]]
    + SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(32,30)
    [SNew(SBorder).BorderImage(Solid).BorderBackgroundColor(Ink).Padding(16)
        .Visibility_Lambda([this]{return Screen == 0 ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed;})
        [SNew(STextBlock).Font(Font(16,true)).ColorAndOpacity(Paper)
            .Text_Lambda([this]{return FText::Format(LOCTEXT("Score", "SCORE  {0}\n{1} élimination(s)"), FText::AsNumber(Score), FText::AsNumber(Kills));})]]
    + SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(32,30)
    [SNew(SBox).WidthOverride(250).Visibility_Lambda([this]{return Screen == 0 ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed;})
        [SNew(SBorder).BorderImage(Solid).BorderBackgroundColor(Ink).Padding(16)
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Font(Font(14,true)).ColorAndOpacity(Paper)
                    .Text_Lambda([this]{return bHealthKnown ? FText::Format(LOCTEXT("Health", "SANTÉ  {0} / {1}"), FText::AsNumber(FMath::CeilToInt(Health)), FText::AsNumber(FMath::RoundToInt(MaximumHealth))) : LOCTEXT("Unavailable", "SANTÉ — indisponible");})]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(SBox).HeightOverride(6)
                    [SNew(SProgressBar).Percent_Lambda([this]{return bHealthKnown ? FMath::Clamp(Health / MaximumHealth,0.f,1.f) : 0.f;})
                        .FillColorAndOpacity_Lambda([this,Amber]{return Health < MaximumHealth * 0.3f ? FLinearColor(0.85f,0.16f,0.11f) : Amber;})]]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8,0,0)[SNew(STextBlock).Font(Font(10)).ColorAndOpacity(Paper).Text(LOCTEXT("PauseHint","ÉCHAP  ·  Pause"))]
            ]]]
    + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0,0,0,60)
    [SNew(SBorder).BorderImage(Solid).BorderBackgroundColor(Ink).Padding(18,10)
        .Visibility_Lambda([this]{return Screen == 0 && !Interaction.IsEmpty() ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed;})
        [SNew(STextBlock).Font(Font(17,true)).ColorAndOpacity(Amber).Text_Lambda([this]{return Interaction;})]]
    + SOverlay::Slot()
    [SNew(SBorder).BorderImage(Solid).BorderBackgroundColor(FLinearColor(0.006f,0.009f,0.013f,0.86f))
        .Visibility_Lambda([this]{return Screen != 0 ? EVisibility::Visible : EVisibility::Collapsed;})
        .HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(SBox).WidthOverride(600)
            [SNew(SBorder).BorderImage(Solid).BorderBackgroundColor(Ink).Padding(40)
                [SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Font(Font(13,true)).ColorAndOpacity(Amber).Text(LOCTEXT("Brand","ZOMBIE SEASONS"))]
                    + SVerticalBox::Slot().AutoHeight().Padding(0,12)[SNew(STextBlock).Font(Font(32,true)).ColorAndOpacity(Paper)
                        .Text_Lambda([this]{return Screen == 2 ? LOCTEXT("Success","Liaison rétablie") : Screen == 3 ? LOCTEXT("Death","Vous avez succombé") : Screen == 4 ? LOCTEXT("Paused","Pause") : LOCTEXT("Welcome","Le silence de l'école");})]
                    + SVerticalBox::Slot().AutoHeight().Padding(0,0,0,24)[SNew(STextBlock).Font(Font(16)).ColorAndOpacity(Paper).WrapTextAt(520)
                        .Text_Lambda([this]{
                            if (Screen == 1) return LOCTEXT("Brief", "L'école a servi de point de rassemblement. Sa radio ne répond plus.\n\nEntrez par la cuisine, retrouvez la radio dans le bureau d'accueil, puis revenez à la cour de livraison.\n\nDéplacements et tir : vos commandes habituelles.\nE : interagir avec l'objet que vous regardez.");
                            if (Screen == 4) return LOCTEXT("PausedBody","La partie est suspendue.");
                            return FText::Format(LOCTEXT("Recap","Durée  {0} min {1} s\nÉliminations  {2}   ·   Score  {3}\nPassage de service ouvert  {4}"), FText::AsNumber(int32(Elapsed)/60), FText::AsNumber(int32(Elapsed)%60), FText::AsNumber(Kills), FText::AsNumber(Score), bPrepared ? LOCTEXT("Yes","Oui") : LOCTEXT("No","Non"));
                        })]
                    + SVerticalBox::Slot().AutoHeight()[SNew(SButton).ContentPadding(FMargin(18,12)).ButtonColorAndOpacity(Amber)
                        .OnClicked_Lambda([this]{if(OnPrimary) OnPrimary(); return FReply::Handled();})
                        [SNew(STextBlock).Font(Font(17,true)).ColorAndOpacity(Paper).Text_Lambda([this]{return Screen == 1 ? LOCTEXT("Start","Commencer l'expédition") : Screen == 4 ? LOCTEXT("Resume","Reprendre") : LOCTEXT("Retry","Rejouer");})]]
                    + SVerticalBox::Slot().AutoHeight().Padding(0,10,0,0)[SNew(SButton).ContentPadding(FMargin(18,10))
                        .Visibility_Lambda([this]{return Screen == 1 ? EVisibility::Collapsed : EVisibility::Visible;})
                        .OnClicked_Lambda([this]{if(OnMenu) OnMenu(); return FReply::Handled();})
                        [SNew(STextBlock).Font(Font(15)).Text(LOCTEXT("Menu","Retour à l'accueil"))]]
                ]]]];
}
#undef LOCTEXT_NAMESPACE
