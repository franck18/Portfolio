# Portfolio Implementation Plan

**Goal:** Moderniser le portfolio public sans perdre le contenu actuel.

**Architecture:** Snapshot des pages en production, HTML statique, styles communs existants et surcharge moderne. Publication limitée aux fichiers modifiés, avec sauvegardes et empreintes.

**Tech Stack:** HTML, CSS, JavaScript existant, Python pour construction et publication.

**Spec:** docs/design.md

1. [x] Identifier le domaine, le dépôt historique et les accès ; sauvegarder le contenu public courant.
2. [x] Finaliser les maquettes des principales sections et extraire les tokens.
3. [x] Construire les deux accueils et les styles communs dans un dossier isolé.
4. [x] Vérifier les pages et contrôles dans Edge, sur ordinateur et mobile.
5. [x] Enregistrer le changement GitHub, sauvegarder les fichiers distants et publier si le transfert OVH est disponible.
6. [x] Contrôler les empreintes publiques et le rendu final ; remettre le résultat et les limites éventuelles.
