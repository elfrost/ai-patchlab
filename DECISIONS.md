# Architecture Decision Records â€” ai-patchlab

> Log chronologique des dÃ©cisions architecturales du projet.
> Format: ADR (Architecture Decision Record) simplifiÃ©.

## Comment utiliser

Quand une dÃ©cision architecturale est prise (choix de tech, design de module, pattern adoptÃ©), ajouter une entrÃ©e ici. Ceci permet de comprendre POURQUOI le code est structurÃ© comme il l'est.

**Quand Ã©crire un ADR ?**

| Ã‰crire un ADR | Sauter |
|---------------|--------|
| Adoption d'un nouveau framework | Bump de version mineure |
| Choix de DB ou de stockage | Bug fix |
| Pattern d'API ou d'auth | DÃ©tail d'implÃ©mentation |
| Architecture sÃ©curitÃ© | Maintenance de routine |
| Pattern d'intÃ©gration externe | Changement de config |

**Cycle de vie:** `Proposed â†’ Accepted â†’ Deprecated â†’ Superseded` (ou `Rejected`)

---

## Templates

Choisir le format selon le poids de la dÃ©cision. Le format **Lite** suffit pour 80% des cas â€” ne sortir le **Standard** que pour les dÃ©cisions structurantes.

### Lite (par dÃ©faut)

```
### ADR-XXX: [Titre court]
**Date:** YYYY-MM-DD
**Status:** accepted | superseded | deprecated
**Decision:** [La dÃ©cision en une phrase]
**Context:** [Pourquoi cette dÃ©cision Ã©tait nÃ©cessaire]
**Consequences:** [Ce que Ã§a implique pour la suite]
```

### Standard (dÃ©cisions structurantes)

InspirÃ© du format MADR. Utiliser quand le choix engage la stack, la sÃ©curitÃ©, ou est difficilement rÃ©versible.

```
### ADR-XXX: [Titre court]
**Date:** YYYY-MM-DD
**Status:** accepted

**Context:** [ProblÃ¨me, contraintes, drivers â€” 3-5 lignes]

**Decision Drivers:**
- [Driver 1 â€” must-have]
- [Driver 2 â€” should-have]

**Considered Options:**
- Option A â€” [pros / cons]
- Option B â€” [pros / cons]
- Option C â€” [pros / cons]

**Decision:** [Option retenue + 1 phrase de raisonnement]

**Consequences:**
- Positive: [ce que Ã§a dÃ©bloque]
- Negative: [ce que Ã§a coÃ»te]
- Risks: [mitigations]
```

### Y-Statement (dÃ©cision rapide Ã  formaliser)

Une seule phrase structurÃ©e. Utile pour capturer une dÃ©cision dÃ©jÃ  prise sans rÃ©Ã©crire un ADR complet.

```
### ADR-XXX: [Titre court]
**Date:** YYYY-MM-DD
**Status:** accepted

In the context of **[contexte]**, facing **[problÃ¨me]**, we decided for **[option]** and against **[alternatives]**, to achieve **[bÃ©nÃ©fice]**, accepting that **[trade-off]**.
```

### Superseding (dÃ©prÃ©cier un ADR existant)

```
### ADR-XXX: [Titre â€” supersedes ADR-YYY]
**Date:** YYYY-MM-DD
**Status:** accepted (supersedes ADR-YYY)

**Context:** ADR-YYY a choisi [X] pour [raison]. Depuis, [ce qui a changÃ©].

**Decision:** Remplacer [X] par [Y].

**Migration:**
- Phase 1: [Ã©tape]
- Phase 2: [Ã©tape]

**Consequences:** [coÃ»ts de migration + bÃ©nÃ©fices long terme]

**Lessons learned from ADR-YYY:** [ce qu'on retient pour les futurs ADRs]
```

### RFC (proposition Ã  dÃ©battre)

Pour les dÃ©cisions qui requiÃ¨rent un round de discussion avant `accepted`. Status reste `Proposed` pendant la review.

```
### ADR-XXX: [Titre â€” RFC]
**Date:** YYYY-MM-DD
**Status:** Proposed

**Summary:** [2 phrases]

**Motivation:** [pourquoi maintenant]

**Detailed Design:** [code, schÃ©mas, contracts]

**Drawbacks:** [coÃ»ts honnÃªtes]

**Alternatives considered:** [au moins 2]

**Unresolved questions:**
- [ ] Question 1
- [ ] Question 2
```

### Bonnes pratiques

- **Ã‰crire l'ADR AVANT l'implÃ©mentation** (pas aprÃ¨s comme excuse)
- **1-2 pages max** â€” un ADR long indique un manque de clartÃ©
- **HonnÃªte sur les trade-offs** â€” inclure les vrais cons, pas juste les pros
- **Linker les ADRs liÃ©s** â€” construire un graphe de dÃ©cisions
- **Ne jamais modifier un ADR `accepted`** â€” crÃ©er un nouveau qui supersede

---

## Decisions

<!-- Ajouter les nouvelles dÃ©cisions en haut (plus rÃ©cent en premier) -->

### ADR-001: Initial project scaffold
**Date:** 2026-05-12
**Status:** accepted
**Decision:** Use EzProject v4 template as project foundation.
**Context:** Need a standardized project structure with built-in quality gates, slash commands, subagents, and reference patterns.
**Consequences:** All code follows CLAUDE.md coding standards. Use examples/ patterns as reference. Use PRP workflow for features.
