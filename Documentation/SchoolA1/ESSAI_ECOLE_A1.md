# École A1 — guide de premier essai

Cadre retenu : France fictive. Unreal Engine 5.5.4.

Ce lot teste les volumes et le scénario local. Les primitives, panneaux et éclairages provisoires ne représentent pas la finition artistique visée.

## Lancer

Ouvrir le niveau `/Game/ZombieSeasons/Maps/Development/L_ZS_School_Expedition`, puis Jouer depuis le PlayerStart. Il utilise le GameMode FPS existant. Les cartes de démarrage globales restent inchangées.

## Parcours

1. Depuis la cour de livraison, entrer dans la cuisine et rejoindre le couloir de service.
2. Rejoindre la loge. Regarder le boîtier et appuyer sur **E** à proximité pour rétablir la liaison.
3. Après trois secondes, l'ordre distant active le secteur B : changement d'éclairage et mise en mouvement des infectés en attente. Les annonces sont actuellement écrites à l'écran.
4. Traverser le gymnase, puis ouvrir le raccourci depuis la cour extérieure avec **E**.
5. Revenir au poste de la cour de départ et appuyer sur **E** pour terminer.

Le passage latéral peut être préparé avant la reconnexion : détour par le petit local au bout du couloir, puis **E** devant sa commande. Il reste facultatif. La sortie ne demande pas de tuer tous les infectés.

## Ce qu'il faut juger en jouant

- Les portes et les angles laissent-ils passer confortablement le personnage ?
- La loge permet-elle de comprendre ce qui vient de se produire dans le gymnase ?
- Peut-on contourner les obstacles et se dégager sans rester accroché ?
- Le détour de préparation donne-t-il une vraie option de retraite ?
- Le retour se comprend-il sans devoir chercher au hasard ?

Faire un essai sans préparer le passage, puis un avec préparation. Relever la durée et les endroits où le déplacement ou la compréhension bloquent. Le test automatisé de navigation ne mesure ni la difficulté réelle ni le plaisir du combat.

## Limites de ce lot

Pas encore de documents narratifs interactifs, de doublage, de sauvegarde d'expédition ou de finition artistique. Les portes s'escamotent pour tester l'ouverture ; leur animation finale reste à produire. Le scénario est un prototype local, sans validation multijoueur. Les capacités de déplacement et de combat proviennent du jeu existant.

La prochaine passe portera sur les défauts du parcours observés en jeu, puis sur une vue du gymnase et son raccord extérieur avec des matériaux et accessoires cohérents avec le cadre français.

## Validation du 6 septembre 2026

- Compilation C++ Unreal 5.5.4 : réussie, DLL liée.
- Test `ZombieSeasons.School.Progression` : réussi.
- Dernier lancement après rechargement de la carte : activation réussie et 16 chemins complets sur 16, sans chemin partiel.
- Correction : reconstruction complète de la navigation au démarrage du scénario A1, car la navigation enregistrée ne couvrait plus tout le parcours après réouverture. Les portes restent prises en compte par la navigation dynamique.
- Captures réelles en DirectX 11 : `ECOLE_A1_GYMNASE.png` et `ECOLE_A1_PLAN.png`. Sur le plan, les plafonds sont masqués uniquement pendant la capture automatique.
- Le test automatique déclenche les états directement : il ne valide pas un parcours humain, les interactions clavier de bout en bout, la difficulté, le multijoueur ou les performances finales.
- Le lancement DirectX 12 de cette session a échoué lors de la création de pipelines graphiques. Aucun réglage graphique global n'a été changé. La validation visuelle ci-dessus porte sur DirectX 11.
- Les annonces restent textuelles et le décor reste un blockout. La finition artistique et l'expédition complète ne sont pas livrées dans A1.
