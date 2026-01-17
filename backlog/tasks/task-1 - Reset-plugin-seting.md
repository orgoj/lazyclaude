---
id: TASK-1
title: Reset plugin seting
status: Done
assignee:
  - '@myself'
created_date: '2026-01-16 12:43'
updated_date: '2026-01-16 14:09'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
V marketplaves view:

Pro plugin mame Enable a Disable. To muze zapisovat primo do scope.

Potrebuji jeste Reset prikaz co toto nastaveni smaze z json daneho scope.

use skil supepower brainsrorm
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Binding R v marketplace_view.py volá action_reset_plugin
- [x] #2 ScopeSelector podporuje action 'reset'
- [x] #3 Metoda _reset_enabled_plugins_json smaže klíč z JSON
- [x] #4 Handler on_scope_selected zpracuje reset akci
- [x] #5 Aplikace se spustí bez chyb
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. marketplace_view.py: Přidat Binding("r", "reset_plugin") a action_reset_plugin() metodu
2. scope_selector.py: Ověřit že podporuje libovolný action string (už by měl)
3. marketplace.py: Přidat _reset_enabled_plugins_json() - smaže klíč místo nastavení hodnoty
4. marketplace.py: V on_scope_selected přidat větev pro action=="reset"
5. Test spuštění aplikace
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementováno:
- Binding R v marketplace_view.py
- action_reset_plugin() metoda
- _run_reset_plugin() worker
- _reset_enabled_plugins_json() - smaže klíč z enabledPlugins

Soubory:
- src/lazyclaude/widgets/marketplace_view.py
- src/lazyclaude/mixins/marketplace.py
<!-- SECTION:NOTES:END -->
