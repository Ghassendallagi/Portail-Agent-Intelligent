# Phase 3 — Référence stable (état validé)

Export de référence des 7 flows Power Automate du projet Attakafulia
(gestion de demandes + validation/rejet/clôture + notifications + SLA/retard),
site `https://attakafulia254.sharepoint.com/sites/PortailIntelligentAgents`.

---

## 1. Les 7 flows actifs

| Flow | ID | State |
|---|---|---|
| Flow_Gestion_Demandes | `ffc2fb9f-dd60-406a-99b0-62ffb16da162` | Started |
| Flow_Validation_Demandes | `3d4c1e5b-50b5-4a81-a42b-24eb1bfe9775` | Started |
| Flow_Rejet_Demandes | `e0cc1316-ea69-421a-b5ba-dba191943b91` | Started |
| Flow_Cloture_Demandes | `aea44a4e-6993-4703-aea9-c1ffc17a81b8` | Started |
| Flow_Notifications_Creation | `73e2d557-cbc1-4d55-bd18-764d4a0dd42f` | Started |
| Flow_Notifications_Mouvements | `1d229c89-e198-49bb-ac9c-606e76112736` | Started |
| Flow_SLA_Retard | `9663da17-2f3f-4742-af8c-5afe22c4f80f` | Started |

Environment PA : `Default-61d70e68-44a8-43ff-9eb3-2279957d445d`

---

## 2. Résumé Phase 3

**a) Architecture Recurrence, structurellement différente des flows Phase 1/2.**
Flow_SLA_Retard tourne sur un trigger `Recurrence` (toutes les 30 min), pas sur
un événement `Created`/`Modified`. Il fait un `Get items` filtré sur les
demandes ouvertes puis un `Apply to each` — logique de balayage périodique,
pas de réaction événementielle.

**b) SLA exprimé en heures, pas en jours.**
Le champ `SLA_Theorique_Jours` (vide, jamais utilisé par aucun flow) a été
supprimé et remplacé par `SLA_Theorique_Heures` sur Services_Siege — permet
un calcul de délai précis à l'heure près, cohérent avec `Date_Soumission`
(DateTime complet).

**c) Deux niveaux de notification SLA.**
Échéance proche (`>=80%` et `<100%` du SLA théorique) et Retard (`>=100%`) —
deux branches distinctes avec des priorités et destinataires différents.

**d) Garde anti-spam à deux champs.**
`Alerte_Retard_Active` (déjà existant) et `Alerte_Echeance_Notifiee` (nouveau,
créé en Phase 3) empêchent la re-notification à chaque passage du Recurrence
(30 min) tant que l'état de la demande n'a pas changé.

**e) Bug `int()` sur décimal corrigé.**
`int(mul(SLA_Theorique_Heures, 0.8))` plantait dès que le résultat n'était pas
un entier exact (ex: `int(6.4)` sur un SLA de 8h). Power Automate exige que
`int()` reçoive une valeur déjà entière — il ne fait pas d'arrondi implicite.
Retiré sur les 3 comparaisons concernées (seuil 80%, et les 2 bornes qui
comparent directement `SLA_Theorique_Heures`) ; les opérateurs
`greaterOrEquals`/`less` acceptent nativement les décimaux, aucun cast requis.

---

## 3. Règles de convention — mise à jour complète

**a)** Choice : comparer/écrire via `/Value`.

**b)** Lookup : jamais `@odata.previous` ; champ Nombre dédié pour tracer un
état précédent.

**c)** Nombre : jamais `empty()` brut ; comparer à `null` directement.

**d)** Égalité entre deux Nombres : `int()`, jamais `string()`.

**e)** Anti-boucle : garde `Statut==cible AND Type!=cible`, PATCH écrit
`Type_Modification=cible` en premier.

**f)** Personne/Groupe : format Claims complet.

**g)** Historique : Create Historique = valeur brute de `Num_Mouvement_Cours`,
PATCH Demande = `add(...,1)`.

**h)** Toute action Create Historique doit écrire `Type_Modification` cohérent
avec le PATCH Demande de la même branche.

**i)** Tout champ Texte reflétant un Lookup doit utiliser `.../Value`
explicite, jamais le contenu brut du Lookup.

**j)** Un `Switch` n'accepte pas `null` en entrée ; garantir la donnée en
amont ou utiliser une chaîne de `Condition`.

**k) Ne jamais utiliser `int()` sur le résultat d'un calcul qui peut produire
un décimal** (ex: `mul(x, 0.8)`), sauf si un arrondi explicite et volontaire
est réellement requis pour l'usage (ex: affichage). `int()` dans Power
Automate exige une valeur déjà entière — il lève une erreur `InvalidTemplate`
("The value cannot be converted to the target type") sur toute fractionnaire,
il n'arrondit ni ne tronque. Les opérateurs de comparaison
(`greaterOrEquals`, `less`, `equals`) acceptent les décimaux nativement :
comparer directement, sans cast.

---

## 4. Mapping SLA validé

| Niveau | Seuil (sur SLA_Theorique_Heures) | Type_Notification | Priority | Destinataire(s) | Garde anti-spam |
|---|---|---|---|---|---|
| Échéance proche | `heures_ecoulees >= SLA*0.8` ET `< SLA` | Reminder | Normal | Gestionnaire_Assigne | `Alerte_Echeance_Notifiee` |
| Retard | `heures_ecoulees >= SLA` | Error | Critical | Gestionnaire_Assigne **+** Responsable_Service (2 notifications distinctes) | `Alerte_Retard_Active` |

Exclusion : les demandes `Statut_Actuel` = `Validé`, `Rejeté` ou `Clôturé` ne
sont jamais évaluées (filtre `Get_Demandes_Ouvertes`).

Valeurs de test actuelles sur Services_Siege : `Technique AUTO = 48h`,
`INFORMATIQUE = 8h` — à ajuster aux vraies valeurs métier avant mise en
production réelle.

---

## 5. Fichiers de ce dossier

- `Flow_Gestion_Demandes_PHASE3_FINAL.json`
- `Flow_Validation_Demandes_PHASE3_FINAL.json`
- `Flow_Rejet_Demandes_PHASE3_FINAL.json`
- `Flow_Cloture_Demandes_PHASE3_FINAL.json`
- `Flow_Notifications_Creation_PHASE3_FINAL.json`
- `Flow_Notifications_Mouvements_PHASE3_FINAL.json`
- `Flow_SLA_Retard_PHASE3_FINAL.json`
- `Phase3_FINAL_README.md` (ce fichier)
