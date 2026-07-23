# Portail Intelligent Agents — Documentation Front Office (application Canvas)

Application Power Apps Canvas destinée aux agents et gestionnaires d'Assurances At-Takafulia pour la soumission, le suivi et le traitement des demandes internes (réclamations, avenants, etc.). Ce document couvre l'intégralité du frontend Canvas (tous rôles confondus) ; le back-end (flows Power Automate, listes SharePoint) n'est pas détaillé ici.

## 1. Rôles et contrôle d'accès

| Rôle | Détection | Portée |
|---|---|---|
| **Agent** | `Agents.Email_Agent = User().Email` | Ses propres demandes uniquement |
| **Gestionnaire** | `Membres_Services.Utilisateur.Email` + `Role.Value = "Gestionnaire"` | Demandes de son service (`Service_ID`) |
| **Superviseur** | idem, `Role.Value = "Superviseur"` | Demandes de son service + alertes SLA |
| **Admin** | idem, `Role.Value = "Admin"` | Toutes les demandes, tous services |
| *(Inconnu)* | Aucune correspondance | Écran `AccesNonConfigure` |

Named Formulas globales (`App.pa.yaml`) :
- `UserRole` = `Coalesce(LookUp(Membres_Services, ...), LookUp(Agents, ...), "Inconnu")` — Membres_Services prioritaire sur Agents (séparation stricte des populations).
- `UserServiceID` / `UserServiceLabel` — pont numérique (`Service_ID.Id`) → libellé texte (`Services_Siege.Title`), utilisé pour scoper les filtres par service.

`App.StartScreen` route vers `Accueil` pour les 4 rôles reconnus, vers `AccesNonConfigure` sinon.

## 2. Architecture de navigation

- **Desktop** : rail latéral fixe (300px) sur les 5 écrans "hub" (Accueil, MesDemandes, FileATraiter, AlertesSLA, MesNotifications) — logo, entrées de navigation filtrées par rôle, badge de notifications non lues, séparateur, bloc nom + rôle utilisateur en bas.
- **Mobile** (`Screen.Size = ScreenSize.Small`) : le rail est masqué, remplacé par une barre de navigation basse (64px, max 5 entrées par rôle).
- Le conteneur de contenu principal de chaque écran hub référence dynamiquement `RailXX.Width` (jamais de largeur codée en dur) pour garantir l'absence de chevauchement.
- **Écrans "focus"** (`DetailDemande`, `NouvelleDemande`) : pas de rail, navigation par flèche retour uniquement — pour éviter de perdre une saisie en cours.
- Navigation contextuelle : `Navigate(Écran, Fade, {ctxTab: "valeur"})` permet de présélectionner un onglet depuis une carte KPI du dashboard (ex. clic sur "À traiter" → ouvre FileATraiter directement sur cet onglet).

## 3. Système visuel

- **Couleur de marque** : bordeaux `RGBA(140,12,20,1)` (choisie plus foncée que le rouge du logo pour rester distincte du rouge d'alerte).
- **Sémantique des couleurs** : rouge vif `RGBA(220,38,38,1)` réservé aux alertes/rejets ; vert `RGBA(6,95,70,1)` réservé aux validations/succès ; gris du logo pour le texte secondaire.
- **Cartes** : coins arrondis, `DropShadow.Semilight` uniforme sur toutes les cartes cliquables (KPI, demandes, notifications, alertes SLA).
- **Cartes KPI** : icône dans une pastille circulaire teintée (44px), chiffre 48px, fond de carte teinté selon la famille de couleur (rouge/vert/bleu/gris pastel).
- **Onglets** : implémentés en `ModernButton` natifs (un bouton par onglet, fond plein bordeaux si actif / transparent sinon, icône + libellé) — voir note technique ci-dessous.
- Aucun effet de survol (hover) sur les cartes : les contrôles utilisés (`GroupContainer`, `ModernButton`) n'exposent aucune propriété de survol dans ce compilateur.

## 4. Écrans

### 4.1 Accueil (dashboard, `StartScreen`)
Tableau de bord d'accueil, contenu entièrement piloté par le rôle :
- En-tête "Bonjour {nom}" + date du jour en toutes lettres.
- Rangée de cartes KPI cliquables (nombre variable selon le rôle) : chaque carte navigue vers l'écran et l'onglet correspondants.
  - **Agent** (3) : Mes demandes en cours, À confirmer (validées), Terminées.
  - **Gestionnaire** (4) : À traiter, En cours (à moi), Traitées, Transférées.
  - **Superviseur** (4) : À traiter, En cours (à moi), Traitées, En retard (SLA).
  - **Admin** (4) : À traiter, Traitées, En retard (SLA), Total demandes.
- Section "Activité récente" : 5 dernières notifications de l'utilisateur, clic → écran Notifications.

### 4.2 MesDemandes (Agent)
Liste des demandes de l'agent connecté, avec :
- Barre de recherche (titre) combinée au filtre d'onglet actif.
- 3 onglets : **En cours** (Soumis + En cours + Validé, par défaut), **Terminées** (Clôturé + Rejeté), **Toutes**.
- Cartes de demande : titre, badge de statut coloré, type, service, date relative, liseré rouge si urgence Urgent/Critique.
- Bouton "+ Nouvelle demande" → `NouvelleDemande`.
- Clic sur une carte → `DetailDemande`.

### 4.3 NouvelleDemande
Formulaire de création pure (`Patch`), sans pièce jointe (les pièces jointes se gèrent après création, depuis `DetailDemande`). Champs : titre, type de demande, service destinataire, niveau d'urgence. Le statut initial est toujours `Soumis`.

### 4.4 DetailDemande (écran focus, multi-origine)
Vue détaillée + chronologie (historique des mouvements). Contenu conditionnel au statut et au rôle :
- **Prendre en charge** (Gestionnaire/Superviseur/Admin) — auto-assignation.
- **Assigner à un gestionnaire** (Superviseur/Admin uniquement) — dialogue avec liste des gestionnaires du service de la demande.
- **Valider / Rejeter / Transférer** — actions de traitement.
- **Confirmer la réception** (Agent, une fois la demande Validée) — clôture.
- Toutes les actions passent par un dialogue de confirmation centralisé (`varActionDialog`), avec Patch + notification de succès/échec.

### 4.5 FileATraiter (Gestionnaire/Superviseur/Admin)
File de travail : recherche (titre + demandeur) + 3 onglets **À traiter** / **Traitées** / **Transférées** (masqué pour Admin). Périmètre par service (Admin = tous services). Accès au dashboard SLA via un bouton d'en-tête (Superviseur/Admin).

### 4.6 AlertesSLA (Superviseur/Admin)
Deux sections empilées : **En retard** (rouge, triées par ancienneté) et **Échéance proche** (ambre), avec périmètre par service (Admin = tous), gestionnaire assigné ou mention "Non assignée", et temps écoulé vs SLA théorique du service.

### 4.7 MesNotifications
Cloche + badge de compteur non-lues sur les 3 écrans concernés (MesDemandes, FileATraiter, AlertesSLA + rail). Écran dédié avec onglets **Non lues** / **Toutes**, marquage lu au clic (navigation vers la demande associée via `ObjectID`, avec gestion des notifications orphelines), et action "Tout marquer comme lu".

### 4.8 AccesNonConfigure
Écran de repli si l'utilisateur connecté n'appartient à aucune population reconnue (ni `Membres_Services`, ni `Agents`).

## 5. Sources de données (SharePoint)

`Demandes`, `Historique_Demandes`, `Membres_Services`, `Agents`, `Services_Siege`, `Notifications`, `Types_Demandes`, `Agences`, `Documents`, `Performance_Mensuelle_Agents`.

## 6. Note technique — fiabilité du rendu AutoLayout

Deux familles de bug de rendu ont été identifiées et corrigées durant le développement :
1. Un conteneur AutoLayout sans hauteur explicite combiné à un enfant `FillPortions` crée une dépendance circulaire non résolue au premier rendu (corrigé par des hauteurs explicites).
2. `LayoutAlignItems`/`LayoutJustifyContent = Center` ne se positionne pas fiablement au premier rendu dans ce compilateur (remplacé par un centrage via padding fixe).

Les onglets, qui ont cumulé plusieurs récidives de ce symptôme malgré des correctifs ciblés, ont finalement été reconstruits avec des contrôles `ModernButton` natifs (contrôles simples, sans sous-structure interne exposée à ces deux familles de bug).

## 7. Limitations connues / backlog

- Recherche par `StartsWith` (préfixe), volontairement non-délégable pour éviter le délai de l'index de recherche SharePoint — acceptable vu le faible volume de données actuel.
- Un bug de troncature de largeur sur la section "Activité récente" du dashboard est en cours de diagnostic (persiste après rafraîchissement complet, cause structurelle encore non identifiée).
- Test multi-rôles complet (bascule Agent/Gestionnaire/Superviseur/Admin) à finaliser avant la démonstration finale.
