# Portail Intelligent Agents — Front Office Canvas App
## Documentation technique complète (PFE — Assurances At-Takafulia)

---

## 1. Contexte

Application **Power Apps Canvas** ("Assurances At-Takafulia — Portail Intelligent Agents") développée dans le cadre d'un PFE. Elle constitue le **front-office** destiné aux agents, gestionnaires, superviseurs et administrateurs pour la soumission, le suivi, le traitement et la supervision SLA des demandes internes (réclamations, avenants, etc.).

- **Environnement Power Platform** : `Default-61d70e68-44a8-43ff-9eb3-2279957d445d`
- **Data source** : liste SharePoint `Demandes` (site `PortailIntelligentAgents`), plus `Historique_Demandes`, `Notifications`, `Membres_Services`, `Agents`, `Services_Siege`.
- **Back-end** (hors périmètre de ce document) : flows Power Automate déclenchés sur les mouvements de statut (`Flow_Notifications_Creation`, `Flow_Assignation`, `Flow_SLA_Retard` — cadence 30 min), qui écrivent l'historique, gèrent les compteurs de mouvement et les indicateurs SLA.
- **Rédaction** de l'app faite intégralement via des fichiers `.pa.yaml` (coauthoring API, pas de manipulation directe dans Power Apps Studio, sauf ajustements ponctuels de l'utilisateur — voir §6.12).
- 8 écrans, tous rôles confondus, **tous fonctionnels et validés par test réel** à la date de rédaction.

---

## 2. Modèle de rôles

### 2.1 Détection (`App.pa.yaml`, Named Formulas)

```
UserRole = Coalesce(
    LookUp(Membres_Services, Utilisateur.Email = User().Email, Role.Value),
    LookUp(Agents, Email_Agent = User().Email, "Agent"),
    "Inconnu"
);
UserServiceID    = LookUp(Membres_Services, Utilisateur.Email = User().Email, Service_ID.Id);
UserServiceLabel = LookUp(Services_Siege, ID = UserServiceID, Title);
```

**Règle de séparation stricte** : `Membres_Services` est prioritaire sur `Agents` dans le `Coalesce` — un même compte ne doit jamais être résolu comme "Agent" s'il existe déjà comme entrée `Membres_Services` (Gestionnaire/Superviseur/Admin). Les deux populations sont volontairement disjointes en donnée réelle.

`App.StartScreen` route les 4 rôles reconnus vers `Accueil` ; tout le reste (`"Inconnu"`) vers l'écran `AccesNonConfigure`.

### 2.2 Les 4 rôles

| Rôle | Table source | Portée métier |
|---|---|---|
| **Agent** | `Agents.Email_Agent` | Ses propres demandes uniquement (créateur = lui) |
| **Gestionnaire** | `Membres_Services` (`Role.Value = "Gestionnaire"`) | Demandes de son service (`Service_ID` → `UserServiceLabel`) |
| **Superviseur** | `Membres_Services` (`Role.Value = "Superviseur"`) | Demandes de son service + tableau de bord SLA |
| **Admin** | `Membres_Services` (`Role.Value = "Admin"`) | Toutes les demandes, tous services, sans filtre de service |

### 2.3 Matrice de visibilité — rail / barre basse / dashboard

| Écran / entrée | Agent | Gestionnaire | Superviseur | Admin |
|---|:---:|:---:|:---:|:---:|
| Accueil | ✅ | ✅ | ✅ | ✅ |
| Mes demandes | ✅ | — | — | ✅ |
| Nouvelle demande (rail desktop) | ✅ | — | — | ✅ |
| Nouvelle demande (barre basse mobile) | ✅ | — | — | ❌ *(exclue mobile uniquement)* |
| File à traiter | — | ✅ | ✅ | ✅ |
| Alertes SLA | — | — | ✅ | ✅ |
| Notifications | ✅ | ✅ | ✅ | ✅ |

> Particularité notée : sur mobile, l'entrée **Nouvelle demande** est retirée pour l'Admin (limite de 5 entrées dans la barre basse, priorité donnée aux entrées de gestion) alors qu'elle reste visible pour l'Admin sur le rail desktop. C'est la seule divergence desktop/mobile de tout le modèle de rôles.

### 2.4 Matrice — cartes KPI du dashboard Accueil

| Carte | Agent | Gestionnaire | Superviseur | Admin |
|---|:---:|:---:|:---:|:---:|
| Mes demandes en cours | ✅ | | | |
| À confirmer (validées) | ✅ | | | |
| Terminées (agent) | ✅ | | | |
| À traiter | | ✅ | ✅ | ✅ |
| Assignées (à moi) | | ✅ | ✅ | |
| Traitées | | ✅ | ✅ | ✅ |
| Transférées | | ✅ | | |
| En retard (SLA) | | | ✅ | ✅ |
| Total demandes | | | | ✅ |

3 cartes pour l'Agent, 4 pour chacun des 3 autres rôles (composition différente à chaque fois — Superviseur perd Transférées mais gagne En retard SLA, Admin perd Assignées/Transférées mais gagne En retard SLA + Total).

### 2.5 Matrice — actions sur `DetailDemande`

| Action | Condition d'affichage |
|---|---|
| **Prendre en charge** | Gestionnaire/Superviseur du service concerné, ou Admin ; demande non assignée ; statut Soumis, ou En cours + dernier mouvement = Transfert |
| **Assigner à un gestionnaire** | Superviseur/Admin uniquement ; mêmes conditions de statut/assignation que ci-dessus |
| **Valider / Rejeter / Transférer** | Gestionnaire/Superviseur du service, ou Admin ; bouton Transférer désactivé (`DisplayMode.Disabled` + tooltip) tant que la demande n'est pas passée par "Prendre en charge" (statut En cours + gestionnaire assigné) |
| **Confirmer la réception (Clôturer)** | Statut Validé ; Admin, ou Agent demandeur de la demande |

Toutes les actions passent par un `varActionDialog` (dialog de confirmation générique, `DialogCard`) avec un `Switch` de cas (`"prendre"`, `"assigner"`, `"valider"`, `"rejeter"`, `"transferer"`, `"cloturer"`) — un seul composant de dialogue pour toutes les actions, la couleur du bouton "Confirmer" et le contenu changeant selon le cas.

---

## 3. Architecture de navigation

### 3.1 Hub vs. focus

- **Écrans "hub"** (5) : `Accueil`, `MesDemandes`, `FileATraiter`, `AlertesSLA`, `MesNotifications` — rail latéral permanent, navigation libre entre eux.
- **Écrans "focus"** (2) : `DetailDemande`, `NouvelleDemande` — pas de rail, flèche retour uniquement (`Back()` pour Detail, multi-origine ; `Navigate` explicite pour Nouvelle) — pour ne pas distraire l'utilisateur d'une saisie ou d'une lecture en cours.
- **Écran d'exception** (1) : `AccesNonConfigure` — aucune navigation, affiché uniquement si `UserRole = "Inconnu"`.

### 3.2 Desktop — rail latéral (300px)

Chaque écran hub réplique la même structure de rail (`Rail{AC,MD,FT,AS,NT}`) :
- Logo (image uploadée via Studio Médias)
- Séparateur
- Entrées de navigation filtrées par rôle (icône + libellé, pastille active bordeaux translucide `RGBA(140,12,20,0.08)`), y compris l'entrée Notifications avec badge rouge de compteur non-lues
- Spacer extensible (`FillPortions=1`, invisible) qui repousse le bloc utilisateur en bas
- Séparateur fin (`RGBA(229,231,235,1)`, 1px)
- Bloc nom + rôle de l'utilisateur connecté

**Règle anti-régression appliquée** (voir §6.9) : le conteneur de contenu principal de chaque écran hub calcule dynamiquement son `X`/`Width` par rapport à `Rail{XX}.Width` (jamais une largeur codée en dur) — un changement futur de largeur du rail ne peut plus jamais créer de chevauchement silencieux.

### 3.3 Mobile — barre basse (64px)

Sur `Screen.Size = ScreenSize.Small`, le rail est masqué et remplacé par une barre de navigation basse (`Bar{AC,MD,FT,AS,NT}`), même filtre de rôle que le rail, maximum 5 entrées.

### 3.4 Navigation contextuelle

`Navigate(Écran, ScreenTransition.Fade, {ctxTab: "valeur"})` — chaque carte KPI du dashboard navigue directement vers l'onglet correspondant de l'écran cible (ex. clic "À traiter" → `FileATraiter` ouvert directement sur l'onglet "À traiter"). Chaque écran cible utilise `Coalesce(ctxTab, valeur_par_défaut)` dans son `OnVisible` pour que le contexte transmis survive, tout en gardant un état par défaut cohérent en navigation directe (rail).

---

## 4. Inventaire des écrans

### 4.1 `Accueil` (dashboard, `StartScreen`)
Tableau de bord piloté entièrement par le rôle : en-tête "Bonjour {User().FullName}" + date du jour en toutes lettres (générée par `Switch(Weekday(...))`/`Switch(Month(...))`, pas de format de date personnalisé — voir §6.4), rangée de cartes KPI (§2.4), section "Activité récente" (5 dernières notifications de l'utilisateur, Gallery cliquable → `MesNotifications`).

### 4.2 `MesDemandes` (Agent, Admin)
Liste personnelle des demandes de l'agent connecté. 3 onglets (`ctxMDTab`) : *En cours* (Soumis/En cours/Validé, défaut), *Terminées* (Clôturé/Rejeté), *Toutes*. Barre de recherche (`ModernTextInput` type Search) filtrant sur `Title` par `StartsWith`. Bouton "+ Nouvelle demande" en en-tête.

### 4.3 `NouvelleDemande` (Agent, Admin)
Formulaire de création pur-Patch (pas de contrôle `Form` natif). 4 champs : Titre (texte), Type de demande (dropdown), Service (dropdown), Niveau d'urgence (radio — valeurs réelles `Faible/Normal/Urgent/Critique`, pas de "Élevé"). Pas de champ pièce jointe ni description (décision produit — voir contrat de Patch en §6.16). Layout centré sur desktop, empilé sur mobile.

### 4.4 `DetailDemande` (tous rôles, multi-origine)
Vue détail en 2 colonnes desktop (empilée mobile) : colonne principale (infos demande, carte Actions conditionnelle §2.5, carte Clôture conditionnelle), colonne latérale (timeline `Historique_Demandes`). Accessible depuis `MesDemandes`, `FileATraiter`, `AlertesSLA`, `MesNotifications` — retour via `Back()`.

### 4.5 `FileATraiter` (Gestionnaire, Superviseur, Admin)
File de travail. 3 onglets (`ctxFTTab`) : *À traiter* (Soumis/En cours/En attente élément/Transféré, scope service sauf Admin = tous), *Traitées* (Validé/Rejeté/Clôturé), *Transférées* (masqué pour Admin — pipeline reconstruit depuis `Historique_Demandes` par `AddColumns`/`RenameColumns`/`Distinct`, non délégable par construction). Barre de recherche sur Titre + nom du demandeur. Bouton "Alertes SLA" en en-tête (Superviseur/Admin uniquement).

### 4.6 `AlertesSLA` (Superviseur, Admin)
Dashboard de supervision SLA. 2 sections empilées : **En retard** (rouge, `Alerte_Retard_Active = true`, tri par ancienneté croissante) puis **Échéance proche** (ambre, `Alerte_Echeance_Notifiee = true && Alerte_Retard_Active = false`). Scope par service (Admin = tous). Chaque carte affiche le gestionnaire assigné ou "⚠ Non assignée" (rouge), les heures écoulées vs. le SLA théorique du service (`LookUp(Services_Siege, ..., SLA_Theorique_Heures)`). Fond de carte teinté rose très doux lorsque *En retard* **et** *Non assignée* sont vrais simultanément (renforcement visuel sans dupliquer le badge texte).

### 4.7 `MesNotifications` (tous rôles)
Centre de notifications. 2 onglets : *Non lues* (défaut), *Toutes*. Carte cliquable = marque lu (`Patch IsRead/ReadDate`) puis navigue vers `DetailDemande` via résolution de `ObjectID` → `LookUp(Demandes, ID = Value(ObjectID))` (gère les notifications orphelines — demande supprimée depuis — avec un `Notify` d'avertissement). Action "Tout marquer comme lu" (`UpdateIf`).

### 4.8 `AccesNonConfigure`
Écran d'exception affiché quand `UserRole = "Inconnu"` (compte non répertorié dans `Agents` ni `Membres_Services`). Pas de navigation.

---

## 5. Système de design

- **Couleur de marque** : bordeaux `RGBA(140,12,20,1)` — choisie plus sombre que le rouge du logo (`RGB(184,16,16)`) pour rester visuellement distincte des couleurs d'alerte.
- **Sémantique stricte des couleurs** : rouge vif `RGBA(220,38,38,1)` réservé aux alertes/rejets/retards SLA ; vert `RGBA(6,95,70,1)` réservé aux validations/succès/clôtures ; gris du logo pour le texte secondaire (`RGBA(112,112,112,1)`) et tertiaire (`RGBA(144,144,144,1)`).
- **Teintes pastel de fond** ("50-level"), réutilisées de façon cohérente sur les cartes KPI, les cartes SLA "non assignée" et les cartes de notification non lues : rouge `RGBA(254,242,242,1)`, vert `RGBA(236,253,245,1)`, bleu `RGBA(239,246,255,1)` (non lu : `RGBA(219,234,254,1)`, plus contrasté), neutre `RGBA(245,245,246,1)`.
- **Cartes** : coins arrondis (8–12px), `DropShadow.Semilight` uniforme sur toutes les cartes cliquables.
- **Cartes KPI** : icône dans une pastille circulaire teintée (44px, `Radius=22`), nombre en 48px gras, fond de carte teinté selon la famille de couleur.
- **Onglets** : `ModernButton` natifs — un bouton par onglet, `Appearance.Primary` (fond bordeaux plein, texte blanc) si actif, `Appearance.Transparent` (texte gris) sinon. Historique de 3 tentatives précédentes échouées avant cette solution — voir §6.6/§6.7.
- **Hover sur cartes cliquables** : `Classic/Button` transparent superposé en façade (bordure `HoverBorderColor` bordeaux au survol) — voir §6.13. Déployé sur toutes les cartes de type Gallery (notifications, activité récente, demandes, file à traiter ×3, alertes SLA ×2). **Non déployé sur les cartes KPI** (limitation structurelle, voir §6.6).
- **Rail / barre basse** : filtrage par rôle strict (§2.3), badge de notifications non lues, séparateur fin entre le contenu de navigation et le bloc utilisateur.

---

## 6. Difficultés techniques Power Apps rencontrées et solutions

Cette section recense, dans l'ordre approximatif de découverte, chaque anomalie ou limite non documentée du compilateur Canvas Apps rencontrée pendant le développement, avec **symptôme**, **cause racine** et **solution retenue**. Elle est écrite pour être réutilisable telle quelle dans la partie "difficultés et solutions" du rapport de PFE.

### 6.1 Formule inline contenant un littéral d'enregistrement casse le parsing YAML

**Symptôme** : une formule `=UpdateContext({x: "y"})` écrite en scalaire YAML plain échoue à la compilation.
**Cause** : le `: ` à l'intérieur du littéral d'enregistrement est interprété par le parseur YAML comme une paire clé/valeur.
**Solution** : toujours écrire ces formules en style bloc littéral YAML (`|-`), jamais en scalaire plain, dès qu'une formule contient un littéral `{...}`.

### 6.2 Propriétés absentes selon le contrôle/variant

Plusieurs incohérences de surface d'API découvertes uniquement à la compilation ou via `describe_control` :
- `Rectangle` (classique) n'a **aucune** propriété `Radius*`.
- La variante `Vertical` de `Gallery` rejette la propriété `Layout`.
- `LayoutOverflow` n'a pas de valeur `Hidden` (seulement `Hide`/`Scroll`).
- Sur `ModernText`, la propriété de couleur s'appelle `Color`, pas `FontColor`.
- L'énumération d'apparence de `Badge` doit être échappée : `='BadgeCanvas.Appearance'.Tint`.
- `Gallery.TemplateWidth`/`TemplateHeight` sont des propriétés de **sortie uniquement** — impossible de les définir, seulement de les lire (`Parent.TemplateWidth` côté enfants).
- `Classic/Button` n'a **pas** de propriété `HoverBorderThickness` (existe pour `HoverFill`/`HoverColor`/`HoverBorderColor` mais pas l'épaisseur) — voir §6.13 pour le contournement.

**Solution générale** : systématiser `describe_control` avant d'utiliser une propriété nouvelle sur un contrôle, plutôt que de supposer une API uniforme entre variantes/contrôles.

### 6.3 `Gallery.OnSelect` avec `Self.Selected` casse le typage de la variable

**Symptôme** : une variable assignée dans un `Gallery.OnSelect` via `Self.Selected` devient de type `Error`, ce qui fait cascader des erreurs partout où la variable est ensuite lue.
**Cause** : `Self.Selected` n'est pas résolu correctement dans ce contexte par le compilateur.
**Solution** : toujours utiliser `ThisItem` dans `Gallery.OnSelect`, jamais `Self.Selected`.

### 6.4 Formats de date personnalisés signalés/instables

Les chaînes de format personnalisées type `"dd/mm/yyyy hh:mm"` passées à `Text(date, "...")` sont signalées par le compilateur comme peu fiables.
**Solution** : utiliser les constantes prédéfinies (`DateTimeFormat.ShortDateTime24`) ou, pour un format textuel français complet ("Jeudi 9 juillet 2026"), construire la chaîne via deux `Switch` imbriqués (`Weekday`, `Month`) plutôt que de s'appuyer sur `Text()` avec un masque.

### 6.5 Renommer un contrôle est parfois obligatoire — changer son `Variant` corrompt ses métadonnées

**Symptôme** : changer le `Variant` d'un contrôle existant (ex. `AutoLayout` → `ManualLayout`) sur un contrôle déjà poussé au serveur provoque des erreurs de parsing en cascade (`AlignInContainer` invalide) sur tous ses enfants survivants.
**Cause** : le serveur associe des métadonnées de layout persistantes au nom du contrôle ; changer le `Variant` sans changer le nom laisse ces métadonnées dans un état incohérent.
**Solution** : **renommer** le contrôle (ce qui force une suppression + recréation côté serveur) dès que son `Variant` ou son `Control` (type) change — jamais de mutation en place. Appliqué systématiquement lors du remplacement des `Rectangle` de clic par des `Classic/Button` (§6.13) : `RectXClick` → `BtnXClick`, jamais une simple réécriture du même nom.

### 6.6 `ManualLayout` enfant d'un `AutoLayout` ignore silencieusement `Width`/`FillPortions` — jamais résolu, contourné 3 fois

C'est la limite la plus coûteuse rencontrée sur ce projet, découverte et re-découverte sur 3 sous-systèmes différents :

1. **Onglets v1/v2 (MesDemandes/FileATraiter)** — un onglet implémenté en `GroupContainer ManualLayout` (rectangle cliquable + libellé + ligne de soulignement) à l'intérieur d'une rangée `AutoLayout` horizontale. Le serveur supprime silencieusement `FillPortions`/`Fill` des conteneurs `ManualLayout` enfants d'`AutoLayout` → onglets à largeur intrinsèque, le 3ᵉ onglet se fait clipper par l'overflow du conteneur alors qu'il est bien présent dans l'arbre Studio (`Visible` intact — faux indice).
   - **Contournement temporaire** : largeur explicite calculée `(Parent.Width - gaps) / nb_onglets`.
2. **Onglets v3** — abandon complet du `ManualLayout` : structure 100% `AutoLayout`, chaque onglet = conteneur vertical `FillPortions=1` (spacer + libellé + ligne empilés, `OnSelect` répliqué sur les 3), sans jamais nester de `ManualLayout` dans un `AutoLayout` sizé. **Diagnostic final (2 régressions plus tard)** : le runtime n'honore ni `FillPortions` ni une formule `Width` explicite sur un `GroupContainer ManualLayout` enfant d'un `AutoLayout` — propriétés bien stockées côté serveur mais ignorées au rendu.
3. **KPI cards (Accueil)** — tentative de superposer un `Classic/Button` de survol (§6.13) sur les cartes KPI. Ces cartes sont des `GroupContainer AutoLayout` (empilement vertical icône/libellé/nombre), pas des items de Gallery (qui, eux, autorisent le positionnement libre de leurs enfants — voir §6.13). La seule façon d'obtenir une vraie superposition serait de convertir le conteneur de carte en `ManualLayout` — mais ce même conteneur est `FillPortions=1` enfant d'un `AutoLayout` horizontal (`KpiRow`) : **exactement** le pattern prouvé cassé au point 1. **Décision** : ne pas reproduire le bug une 3ᵉ fois — les cartes KPI restent sans survol, clic conservé via les sous-contrôles (icône/libellé/nombre).

**Règle définitive retenue** : ne **jamais** nester un `GroupContainer Variant: ManualLayout` sizé (`FillPortions` ou `Width` relatif) à l'intérieur d'un `GroupContainer Variant: AutoLayout`. Si un besoin de positionnement libre apparaît sur un enfant d'`AutoLayout`, chercher une solution 100% `AutoLayout` (FillPortions/Stretch) ou accepter la limitation plutôt que d'improviser un contournement non éprouvé.

### 6.7 Circularité de layout au premier rendu : `Height` manquant sur un conteneur dont un enfant utilise `FillPortions`

**Symptôme** (onglets, 3ᵉ récidive avant fix définitif) : la rangée d'onglets s'affiche vide au premier chargement, se corrige en basculant une propriété d'alignement dans Studio ("collé" ensuite).
**Cause racine réelle** : chaque conteneur d'onglet (`AutoLayout` vertical, `FillPortions=1` dans la rangée horizontale) n'avait pas de `Height` explicite — sa hauteur dépendait du contenu, mais l'un de ses enfants (le rectangle de zone cliquable) demandait `FillPortions=1` ("occuper l'espace restant"), ce qui nécessite de connaître la hauteur du conteneur *avant* qu'elle ne soit résolue → dépendance circulaire non résolue au premier rendu.
**Solution** : donner à chaque conteneur d'onglet un `Height` explicite identique à celui de la rangée (`=48`) — élimine la référence circulaire, indépendamment de la valeur de `LayoutAlignItems` du parent.
**Règle générale** : un enfant `AutoLayout` qui se dimensionne via `FillPortions` contre une hauteur (ou largeur) **non définie explicitement** de son parent immédiat est fragile, même sans aucun `ManualLayout` impliqué — toujours donner une taille explicite au parent immédiat dans ce cas.

### 6.8 `LayoutAlignItems.Center` / `LayoutJustifyContent.Center` non fiable au premier rendu

**Symptôme** : 9 badges d'icônes KPI (cercle 44px, icône centrée via `Center`/`Center`) s'affichent avec un cercle vide (fond/nombre/libellé corrects, seule l'icône manque) au premier chargement, se corrigeant sur un rafraîchissement complet du navigateur.
**Diagnostic** : `Center`/`Center` n'était utilisé **nulle part ailleurs** dans l'app (100+ autres conteneurs `AutoLayout` utilisent `Start`/`End`/`Stretch` sans problème) — confirme que le problème est spécifique à ce couple de valeurs, pas à un défaut de `Visible`/rôle asynchrone (le reste de la carte s'affichait correctement dès le premier rendu).
**Solution** : remplacer `Center`/`Center` par `LayoutAlignItems.Start` + un padding fixe calculé sur les 4 côtés (`(taille_conteneur − taille_enfant) / 2`, ex. 9px pour une icône 26px dans un cercle 44px).
**Règle définitive** : ne jamais utiliser `Center`/`Center` pour centrer un élément dans ce compilateur — toujours `Start` + padding fixe calculé.

### 6.9 Formule `Width` correcte mais jamais propagée à `TemplateWidth` d'un `Gallery` profondément nesté

**Symptôme** : la Gallery "Activité récente" (dashboard) affichait des cartes visiblement trop étroites/tronquées, malgré une formule `Width: =Parent.Width - 56` identique en forme à celle utilisée avec succès par 4 autres Galleries du même projet (`GalleryDemandes`, `GalleryATraiter`, `GalleryTraitees`). Persistait après rafraîchissement complet du navigateur (donc **pas** un problème de premier rendu comme §6.7/§6.8).
**Méthode de diagnostic** : fixer `Width` à une valeur littérale codée en dur (`=1100`) pour vérifier si le conteneur parent était réellement la contrainte → les cartes s'affichaient alors correctement en pleine largeur, prouvant que la formule elle-même ne se résolvait pas vers `TemplateWidth`.
**Cause identifiée** : `Gallery` (contrôle "Classic") enfant d'un conteneur `AutoLayout` gagne une propriété d'entrée `AlignInContainer` (`SetByContainer`/`Start`/`Center`/`End`/`Stretch`, confirmée via `describe_control`) — c'est le mécanisme natif attendu pour dimensionner un contrôle Classic le long de l'axe transverse d'un `AutoLayout`, distinct d'une formule `Width` calculée à la main. Cette Gallery n'avait jamais reçu de directive de dimensionnement le long de cet axe.
**Solution** : remplacer la formule `Width` par `AlignInContainer: =AlignInContainer.Stretch`. Après push, la propriété disparaît du YAML synchronisé (le serveur élague les valeurs par défaut) — signe que `Stretch` était déjà la valeur effective une fois explicitement demandée.
**Règle définitive** : un contrôle Classic (ex. `Gallery`) enfant d'un `AutoLayout` doit utiliser `AlignInContainer` pour occuper correctement l'espace disponible — une formule `Width` manuelle ne se propage pas fiablement à `TemplateWidth`/à la largeur rendue, même si la formule identique fonctionne sur d'autres instances du même contrôle ailleurs dans l'app.

### 6.10 Named Formulas de couleur non résolues sur des contrôles profondément imbriqués

**Symptôme** : conteneurs noirs / texte invisible en Play réel sur `DetailDemande`, alors que les mêmes Named Formulas de couleur (`ColorAccent`, etc., définies dans `App.Formulas`) fonctionnaient parfaitement sur `MesDemandes`.
**Cause observée** : les Named Formulas de couleur peuvent échouer à se résoudre au runtime sur des contrôles nichés à 4 niveaux ou plus de profondeur — `DetailDemande` a une hiérarchie de conteneurs plus profonde que `MesDemandes`.
**Solution** : sur `DetailDemande`, remplacement systématique des Named Formulas par des littéraux `RGBA(...)` directs. `MesDemandes` (nesting plus faible) conserve les Named Formulas sans problème. Pas de règle de profondeur exacte établie — traité au cas par cas selon la profondeur réelle observée.

### 6.11 Le serveur réordonne arbitrairement les contrôles nouvellement créés — toujours pousser deux fois

**Symptôme** : après un premier `compile_canvas` qui crée de nouveaux contrôles, leur ordre de déclaration dans l'arbre ne correspond pas à l'ordre du YAML local.
**Cause** : le serveur applique l'ordre du YAML uniquement aux contrôles **déjà existants** — les contrôles fraîchement créés sont insérés à une position arbitraire lors du premier push.
**Solution systématique** : relancer `compile_canvas` une seconde fois immédiatement (mêmes fichiers, sans modification) — le second push réordonne les contrôles existants pour correspondre au YAML. Parfois un contrôle reste mal placé même après le 2ᵉ push (observé une fois) → toujours `sync_canvas` vers un répertoire de contrôle et diffs les lignes `^ *- Name:` (jamais une recherche d'occurrence brute — des formules comme `Reset(X)` polluent le diff) jusqu'à obtenir un ordre strictement identique.

### 6.12 Sauvegarde manuelle Studio par l'utilisateur peut réordonner des sections non éditées

Une sauvegarde par l'utilisateur dans Power Apps Studio peut réordonner des sections de l'app qui n'ont pas été touchées par cette édition manuelle (observé : titre d'une section poussé en dernière position sur un écran alors que l'utilisateur n'avait édité que la largeur des onglets sur un autre écran).
**Règle de travail adoptée** : toujours `sync_canvas` vers un répertoire scratch **avant** toute modification, pour rapatrier d'éventuels ajustements manuels de l'utilisateur et re-pousser l'ordre local si besoin — jamais modifier "à l'aveugle" sur la base des fichiers locaux seuls sans vérifier l'état serveur au préalable.

### 6.13 `Classic/Button` expose `HoverBorderColor` — contrairement à `ModernButton`/`GroupContainer` qui n'ont aucun survol natif

**Découverte par élimination** : `describe_control` sur `Button`/`ModernButton` (famille FluentV9) et `GroupContainer` (utilisé pour toutes les cartes cliquables de l'app) ne révèle **aucune** propriété préfixée `Hover*`, confirmant l'absence totale de mécanisme de survol natif pour ces contrôles. En revanche, `Classic/Button` (nom exact dans `list_controls`, famille Classic, distinct de `Button`) expose bel et bien `HoverFill`/`HoverColor`/`HoverBorderColor` (+ `PressedFill`/`PressedColor`/`PressedBorderColor`) en propriétés d'entrée **et** de sortie.

**Solution retenue — superposition transparente** : sur chaque carte cliquable de type item de Gallery, remplacer le rectangle de zone cliquable transparent (`Rectangle`, sans survol possible) par un `Classic/Button` transparent occupant les mêmes `X=0,Y=0,Width=Parent.TemplateWidth,Height=Parent.TemplateHeight` :
```
Fill / HoverFill / PressedFill        : transparent RGBA(0,0,0,0)
BorderColor                            : transparent RGBA(0,0,0,0)
HoverBorderColor / PressedBorderColor  : bordeaux RGBA(140,12,20,1)
BorderThickness                        : =2 (constante, invisible tant que la couleur reste transparente)
RadiusTopLeft/TopRight/BottomLeft/BottomRight : identique au rayon de la carte
```
**Piège découvert en cours de route** : `HoverBorderThickness` **n'existe pas** comme propriété sur `Classic/Button` (erreur de compilation "Unknown property"). Contournement : garder une **épaisseur de bordure constante**, invisible au repos car la couleur est transparente — seule la **couleur** change au survol (`HoverBorderColor`), pas l'épaisseur. Le résultat visuel est identique à un contournement par épaisseur variable.

**Pourquoi cette technique ne marche que sur les items de Gallery** : un template de `Gallery` se comporte comme un mini-canevas à positionnement libre pour ses enfants directs (le contenu de la carte et le bouton de survol coexistent au même `X/Y`, sans flux). Un `GroupContainer AutoLayout` classique (ex. les cartes KPI, §6.6 point 3) ne le permet pas — ses enfants sont empilés en flux, pas superposés.

**Un seul point de clic — anti double-déclenchement** : chaque Gallery concernée avait, en plus du rectangle/bouton de clic, son propre `Gallery.OnSelect` répliquant la même logique en "filet de sécurité" (héritage des tout premiers écrans). Lors du remplacement, ce `OnSelect` de niveau Gallery a été **supprimé** partout où le nouveau bouton devenait le point de clic unique, pour éliminer tout risque de double-déclenchement (ex. double `Patch` de marquage-lu, double `Navigate`).

**Déployé sur** : `MesNotifications`, `Accueil` (Activité récente), `MesDemandes`, `FileATraiter` (3 onglets/galeries), `AlertesSLA` (2 sections). **Non déployé** sur les cartes KPI du dashboard (§6.6 point 3).

### 6.14 `compile_canvas` peut afficher "Validation FAILED" alors que le push a réussi

Le rapport de validation affiche "✗ Validation FAILED" dès qu'il existe des **avertissements** (warnings), même en l'absence de toute erreur — mais le contenu est bel et bien poussé au serveur (vérifié systématiquement par `sync_canvas`). Ne pas interpréter ce libellé comme un échec réel sans lire le détail des diagnostics.

### 6.15 Avertissements de délégation — comportement et faux-positifs

- Toute Named Formula qui interroge une source de données est signalée "non déléguable" à **chaque** site de référence, indépendamment de sa structure interne (ex. `UserRole`) — accepté car portant sur des listes de référence minuscules.
- `StartsWith(colonne, valeur)` (recherche texte) n'est **jamais** délégable dès que le nom de colonne apparaît en 2ᵉ argument dans ce connecteur SharePoint — accepté en connaissance de cause plutôt qu'utiliser `Search()` (qui délègue mais lit un index de recherche en retard sur les écritures live — risque de fraîcheur inacceptable pour un outil de workflow actif).
- Une colonne de type lookup accédée via `.Id` **ne délègue pas**, mais la même colonne accédée via `.Value` **délègue**.
- `AddColumns`/`RenameColumns`/`Distinct` prennent des **identifiants nus** (pas des chaînes) dans ce compilateur, alors que `SortByColumns` garde des noms de colonnes en chaînes — incohérence de syntaxe entre fonctions à connaître.
- Méthode d'audit adoptée quand le nombre total d'avertissements change entre deux sessions : catégoriser chaque ligne par nom de contrôle et croiser avec ce qui a **réellement** été édité dans la session (jamais deviné) — tout avertissement sur un contrôle/une formule non touchés est par définition préexistant, quel que soit le total annoncé par une session précédente.

### 6.16 `@odata.type` requis sur un `Patch` de colonne Personne en mise à jour + contrat de Patch à la création

Lors d'un `Patch` sur une colonne SharePoint de type Personne (`Gestionnaire_Assigne`) en **mise à jour** (self-assign "Prendre en charge", assignation par Superviseur), l'annotation `'@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser"` doit être conservée dans le littéral d'enregistrement patché — sans elle, la colonne Personne n'est pas correctement résolue côté connecteur. Ce format a été validé une première fois via un test REST direct sur SharePoint (`MERGE` → 204) avant d'être répliqué dans les deux Patchs Power Fx concernés (auto-assignation et assignation par un tiers, cette dernière utilisant `DdGestionnaireCible.Selected.Utilisateur.*` comme source au lieu de `User()`).

Contrat de `Patch` à la création d'une demande (`NouvelleDemande`, vérifié contre les définitions de colonnes réelles) : `Statut_Actuel = {Value:"Soumis"}` explicite ; `Num_Mouvement_Cours = 1` explicite (convention flow : les flows écrivent la valeur brute dans l'historique puis incrémentent) ; `Alerte_Retard_Active = false` explicite (colonne sans défaut — naît `null` sinon) ; `Alerte_Echeance_Notifiee` omis (défaut `0`) ; `Date_Dernier_Mouvement` omis (`null` jusqu'au premier mouvement de flow) ; `Agent_Demandeur` = enregistrement Claims `i:0#.f|membership|` + `Lower(User().Email)` ; `Niveau_Urgence` réel = `Faible/Normal/Urgent/Critique` (jamais "Élevé", bug latent corrigé au tout début du projet).

### 6.17 Anomalie d'environnement de test — session Chrome corrompue vs. formule incorrecte

Une erreur générique "Erreur réseau lors de l'utilisation de la fonction Patch : la demande n'a pas été envoyée", reproductible de façon répétée, s'est révélée être une **session de navigateur corrompue** (le même `Patch`, code strictement identique, fonctionnait immédiatement sous Edge après avoir échoué en boucle sous Chrome). Un test REST SharePoint direct (MERGE 204) a permis de confirmer que colonne/permissions/flows n'étaient pas en cause avant de suspecter l'environnement de test plutôt que le code.
**Leçon méthodologique** : face à une erreur réseau Power Apps généralisée et reproductible sur toutes les formules `Patch`, tester un autre navigateur **avant** de déboguer la formule.

### 6.18 Outils d'automatisation navigateur non fiables pour tester le canevas Play

Le canevas Play d'une app Power Apps chargé dans un onglet Chrome piloté par automatisation (`claude-in-chrome`) charge la coquille de l'application mais le canevas de rendu ne s'affiche jamais (gel du moteur de rendu) — cet outil n'a **pas** pu être utilisé pour valider visuellement le comportement en Play ; toute validation UI réelle (y compris le survol souris, §6.13) nécessite un test manuel par un humain avec une souris physique.

---

## 7. Historique de développement (résumé chronologique par commit)

| Étape | Contenu |
|---|---|
| État stable initial | `MesDemandes` + `DetailDemande` 2 colonnes desktop |
| Responsive | `DetailDemande` 2 colonnes desktop / empilé mobile |
| `NouvelleDemande` | Formulaire Patch bout-en-bout validé (app → SharePoint → flows) |
| Filtres par rôle | `FileATraiter` vérifié statiquement sur données réelles |
| Actions | Valider/Rejeter/Transférer/Clôturer implémentées |
| Onglets FileATraiter | 3 onglets + bouton "Prendre en charge" |
| Onglets MesDemandes | 3 onglets, même pattern, 1ᵉʳ passage composant onglet |
| Fix régression onglets | Largeur explicite (contournement `ManualLayout`, temporaire) |
| Onglets v3 | Abandon `ManualLayout`, structure 100% `AutoLayout` |
| Ajustements manuels utilisateur | Studio, rapatriés par sync (règle sync-avant-modif adoptée) |
| `AlertesSLA` | Dashboard SLA Superviseur/Admin, validé par test réel |
| `MesNotifications` | Cloche + badge, écran notifications, marquage lu — **tous les écrans fonctionnels terminés** |
| Polish visuel Phase A | Rebrand bordeaux, dashboard `Accueil`, rail 240px, barre basse mobile |
| Polish visuel Phase B (1) | Icônes KPI, respiration dashboard, contraste notifications, séparateur rail, suppression barre d'accent, **fix largeur `GalleryActivite`** (`AlignInContainer.Stretch`) |
| Polish ciblé | Fond teinté cartes SLA non assignées ; **généralisation du survol** (`Classic/Button`) à toutes les cartes de type Gallery ; exclusion documentée des cartes KPI |

---

## 8. État final

Les 8 écrans sont fonctionnels, validés par test réel (multi-rôles), `App Checker` propre (0 erreur), baseline stable de warnings de délégation entièrement auditée et justifiée (voir §6.15). Aucun point bloquant ouvert au moment de la rédaction ; seule limitation connue et documentée : absence de survol sur les cartes KPI du dashboard (§6.6, §6.13).
