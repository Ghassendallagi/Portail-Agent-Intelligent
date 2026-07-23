# Phase 2 — Référence stable (état validé)

Export de référence des 6 flows Power Automate du projet Attakafulia
(gestion de demandes + validation/rejet/clôture + notifications), site
`https://attakafulia254.sharepoint.com/sites/PortailIntelligentAgents`.

---

## 1. Les 6 flows actifs

| Flow | ID | State |
|---|---|---|
| Flow_Gestion_Demandes | `ffc2fb9f-dd60-406a-99b0-62ffb16da162` | Started |
| Flow_Validation_Demandes | `3d4c1e5b-50b5-4a81-a42b-24eb1bfe9775` | Started |
| Flow_Rejet_Demandes | `e0cc1316-ea69-421a-b5ba-dba191943b91` | Started |
| Flow_Cloture_Demandes | `aea44a4e-6993-4703-aea9-c1ffc17a81b8` | Started |
| Flow_Notifications_Creation | `73e2d557-cbc1-4d55-bd18-764d4a0dd42f` | Started |
| Flow_Notifications_Mouvements | `1d229c89-e198-49bb-ac9c-606e76112736` | Started |

Environment PA : `Default-61d70e68-44a8-43ff-9eb3-2279957d445d`

---

## 2. Correctifs Phase 2

**a) Type_Modification manquant sur les entrées Historique (Flow_Gestion_Demandes).**
Les actions "Créer Historique" (Assignation, Transfert, Réaffectation) ne renseignaient
jamais `Type_Modification` — le champ restait vide. Cela plantait le `Switch` de
Flow_Notifications_Mouvements dès qu'il lisait un item Historique ainsi produit
(`Switch` n'accepte pas `Null` en entrée, contrairement à une `Condition`).

**b) Service_A_Ce_Moment écrit comme objet Lookup sérialisé (Flow_Gestion_Demandes).**
Les branches Transfert et Réaffectation écrivaient `Service_A_Ce_Moment` avec
`triggerOutputs()?['body/Service_Actuel_ID']` (objet Lookup brut) au lieu de
`.../Service_Actuel_ID/Value` (texte). Le champ contenait donc un JSON sérialisé
entier au lieu du nom du service, ce qui cassait le filtre
`$filter=Title eq '...'` du cas Transfert dans Flow_Notifications_Mouvements
(0 résultat → Destinataire vide → erreur SharePoint "The specified user could
not be found").

---

## 3. Règles de convention — mise à jour complète

**a) Champs Choix** — comparer/écrire via `/Value`.

**b) Champs Lookup** — ne jamais utiliser `@odata.previous` dessus ; utiliser un
champ Nombre dédié pour tracer un état précédent (pattern C14).

**c) Champs Nombre** — ne jamais utiliser `empty()` brut dessus ; comparer à `null`
directement (pattern C14-bis) ou `empty(string(...))`.

**d) Comparaison d'égalité entre deux Nombres** — caster en `int()`, jamais en
`string()`.

**e) Anti-boucle** — garde `Statut==cible AND Type!=cible`, PATCH écrit
`Type_Modification=cible` en premier.

**f) Champs Personne/Groupe** — toujours format Claims complet
`i:0#.f|membership|<email>`.

**g) Historique — numérotation des mouvements** — Create Historique utilise la
valeur brute de `Num_Mouvement_Cours` (sans `add`), le PATCH Demande utilise
`add(...,1)`. Jamais `add()` aux deux endroits (fix Phase 1).

**h) Toute action Create Historique doit écrire `Type_Modification`** avec la
même valeur que le PATCH Demande de la même branche — sinon tout flow en aval
qui lit ce champ sur Historique (ex: dispatch par type de mouvement) reçoit
`null` de façon imprévisible.

**i) Tout champ Texte qui reflète un Lookup** (ex: `Service_A_Ce_Moment`) doit
utiliser explicitement `.../Value` — jamais le contenu dynamique brut du
Lookup, qui sérialise l'objet entier (`{"@odata.type":...,"Id":...,"Value":...}`)
en JSON dans le champ texte.

**j) Un `Switch` n'accepte pas `null` en entrée**, contrairement à un `If`/`Condition`
qui tolère très bien une comparaison avec `null` (renvoie simplement `false`).
Tout champ Choice lu par un `Switch` doit être garanti non-null en amont
(cf. règle h), ou remplacé par une chaîne de `Condition` imbriquées si la
donnée source ne peut pas être garantie complète. **Note d'implémentation** :
dans ce projet, le correctif retenu a été de garantir la donnée en amont
(règle h) plutôt que de blinder le `Switch` lui-même (pas de `coalesce()`
ajouté sur l'expression) — à garder en tête si un futur item Historique est
créé par un moyen qui ne respecte pas la règle h (ex: saisie manuelle), le
`Switch` replantera.

---

## 4. Mapping notifications validé

| Événement (Type_Modification) | Type_Notification | Priority | Destinataire |
|---|---|---|---|
| Nouvelle demande (création Demande) | Information | Normal | Responsable_Service (du service initial) |
| Assignation | Information | Normal | Agent_Demandeur |
| Transfert | Warning | Normal | Responsable_Service (du nouveau service) |
| Validation | Validation | High | Agent_Demandeur |
| Rejet | Refus | High | Agent_Demandeur **+** Responsable_Service (service actuel) — 2 notifications distinctes |
| Clôture | Success | Normal | Agent_Demandeur |
| Réaffectation | — | — | **Aucune notification** (évite le doublon avec l'Assignation qui suit) |
| Tout autre / inconnu | — | — | Ignoré proprement (branche `default`) |

Email envoyé pour tous les types actuellement (pas de filtre par Priority) —
marqué `// TODO Phase 2.1` dans chaque action d'envoi pour un futur ajustement
par volume.

---

## 5. Fichiers de ce dossier

- `Flow_Gestion_Demandes_PHASE2_FINAL.json`
- `Flow_Validation_Demandes_PHASE2_FINAL.json`
- `Flow_Rejet_Demandes_PHASE2_FINAL.json`
- `Flow_Cloture_Demandes_PHASE2_FINAL.json`
- `Flow_Notifications_Creation_PHASE2_FINAL.json`
- `Flow_Notifications_Mouvements_PHASE2_FINAL.json`
- `Phase2_FINAL_README.md` (ce fichier)
