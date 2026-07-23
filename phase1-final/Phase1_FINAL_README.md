# Phase 1 — Référence stable (état validé)

Export de référence des 4 flows Power Automate agissant sur la liste **Demandes**
(`20c94652-f1e6-4f89-9736-cde7b553c412`), site
`https://attakafulia254.sharepoint.com/sites/PortailIntelligentAgents`.

Les items de test (Demandes + Historique_Demandes) ont été nettoyés manuellement
après validation — ce dossier documente l'état des **flows**, pas des données.

---

## 1. Les 4 flows actifs

| Flow | ID | State |
|---|---|---|
| Flow_Gestion_Demandes | `ffc2fb9f-dd60-406a-99b0-62ffb16da162` | Started |
| Flow_Validation_Demandes | `3d4c1e5b-50b5-4a81-a42b-24eb1bfe9775` | Started |
| Flow_Rejet_Demandes | `e0cc1316-ea69-421a-b5ba-dba191943b91` | Started |
| Flow_Cloture_Demandes | `aea44a4e-6993-4703-aea9-c1ffc17a81b8` | Started |

Environment PA : `Default-61d70e68-44a8-43ff-9eb3-2279957d445d`

---

## 2. Historique des correctifs (Flow_Gestion_Demandes)

| # | Correctif | Résumé |
|---|---|---|
| C1 | Condition racine | Évite faux positifs sur items sans Gestionnaire |
| C2 | Condition_2 Terme 1 | Ajout garde `Statut ≠ Soumis` |
| C3 | Condition_2 Terme 2 | Détection changement de service |
| C9 | Condition_1 révisée | Assignation valable sur Nouvelle demande ET Réaffectation |
| C10 | Condition_3 Terme 1 | Garde Gestionnaire non vide |
| C11 | Condition_2 Terme 3 | Garde contre `@odata.previous = null` (faux Transfert lors Assignation) |
| C12 | Condition_3 Terme 2 | `Type != "Réaffectation"` → `Type == "Transfert"` — corrige la boucle infinie Réaffectation↔Assignation |
| C13 | Condition_2 Termes 2+3 | `Service_Actuel_ID@odata.previous` → `Service_Actuel_IDId@odata.previous` (lookup ID vs objet) |
| C14 | Condition_2 (root cause) | `@odata.previous` n'existe jamais sur les Lookup — remplacé par champ dédié `Service_Precedent_ID` (Nombre) |
| C14-bis | Condition_2 Terme 3 | `empty()` sur Nombre lève BadRequest — remplacé par `not(equals(..., null))` |
| fix Num Historique | Create Historique (Validation/Rejet/Clôture) | `add(Num_Mouvement_Cours,1)` → valeur brute, pour aligner sur la convention de Flow_Gestion_Demandes et éviter un numéro sauté |

---

## 3. Règles de convention — à respecter sur tout futur flow de cette liste

**a) Champs Choix** (`Statut_Actuel`, `Type_Modification`, `Niveau_Urgence`, ...)
Toujours comparer via `/Value` :
`triggerOutputs()?['body/Statut_Actuel/Value']` — jamais le champ brut.

**b) Champs Lookup** (`Service_Actuel_ID`, `Agent_ID`, ...)
Ne jamais utiliser `@odata.previous` dessus — le connecteur SharePoint ne
l'émet pas pour les Lookup. Pour connaître un état précédent : créer un champ
Nombre dédié, mis à jour explicitement à chaque PATCH pertinent (pattern C14).

**c) Champs Nombre**
Ne jamais utiliser `empty()` brut dessus — Power Automate lève `BadRequest`
("empty() expects object/array/string, got Float") dès que la valeur est
non-nulle. Toujours `empty(string(leChamp))`, ou comparer directement à `null`.

**d) Comparaison d'égalité entre deux Nombres**
Caster en `int()`, jamais en `string()` — un Nombre SharePoint peut sérialiser
`"2"` vs `"2.0"` et fausser une comparaison de chaîne.

**e) Anti-boucle (obligatoire sur tout flow déclenché par create/modify)**
Garde = `Statut_Actuel/Value == "<cible>" AND Type_Modification/Value != "<cible>"`.
La première chose écrite dans le PATCH est `Type_Modification = "<cible>"`.
Au re-trigger causé par ce PATCH, la garde devient FALSE automatiquement.
Ne jamais utiliser une garde par négation large (`Type != "Autre_Chose"`) —
c'est ce qui avait causé la boucle Assignation↔Réaffectation (C10→C12).

**f) Champs Personne/Groupe** (`Gestionnaire_A_Ce_Moment`, `Actionneur`, ...)
Toujours au format Claims complet : `i:0#.f|membership|<email>` — jamais
l'email brut.

**g) Historique — numérotation des mouvements**
- Create Historique : `item/Num_Mouvement = triggerOutputs()?['body/Num_Mouvement_Cours']`
  (valeur **brute**, sans `add`)
- PATCH Demande : `item/Num_Mouvement_Cours = add(triggerOutputs()?['body/Num_Mouvement_Cours'], 1)`

Ne jamais mettre `add(...,1)` aux deux endroits — cela saute un numéro dans
Historique_Demandes (bug rencontré et corrigé sur Validation/Rejet/Clôture).

---

## 4. Séquence canonique de référence (modèle théorique)

Scénario Ahmed Ben Salem → Youssef Gharbi, tel que validé par les tests manuels
(données réelles nettoyées depuis — ceci sert de modèle pour le prochain cycle
de tests) :

| Num_Mouvement | Type_Modification | Statut_Actuel | Déclenché par |
|---|---|---|---|
| 1 | Nouvelle demande | Soumis | Création |
| 2 | Assignation | En cours | Flow_Gestion_Demandes — Condition_1 |
| 3 | Transfert | En cours | Flow_Gestion_Demandes — Condition_2 |
| 4 | Réaffectation | Soumis | Flow_Gestion_Demandes — Condition_3 |
| 5 | Assignation | En cours | Flow_Gestion_Demandes — Condition_1 (2e passage) |
| 6 | Validation | Validé | Flow_Validation_Demandes |
| 7 | Clôture | Clôturé | Flow_Cloture_Demandes — seul flow autorisé à écrire `Date_Cloture` |

Rejet (branche alternative, depuis "En cours", non illustrée dans ce cycle) :
`Statut_Actuel = "Rejeté"`, `Type_Modification = "Rejet"`, motif consigné dans
`Historique_Demandes.Commentaire_Action` (alimenté par `Motif_Rejet` si renseigné).

---

## 5. Fichiers de ce dossier

- `Flow_Gestion_Demandes_PHASE1_FINAL.json`
- `Flow_Validation_Demandes_PHASE1_FINAL.json`
- `Flow_Rejet_Demandes_PHASE1_FINAL.json`
- `Flow_Cloture_Demandes_PHASE1_FINAL.json`
- `Phase1_FINAL_README.md` (ce fichier)
