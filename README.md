# Refonte de franckraymond.tech

Refonte visuelle du portfolio public : typographie Geist, bleu cobalt, fonds blancs et gris bleutés, accueil avec photographie originale, projets numérotés, expériences et contact plus lisibles. Les thèmes, les traductions et les démonstrations existantes sont conservés.

La photographie d'origine n'est ni retouchée ni remplacée. Les maquettes générées ne sont pas des ressources du site.

Le dépôt historique `franck18/Portfolio` ne correspondait plus au site OVH. Ce changement fournit donc une surcouche de publication dans `franckraymond-tech/`, séparée des anciens fichiers. Les autres ressources publiques existantes sur OVH restent nécessaires : ce dossier n'est pas une copie autonome du site complet.

## Préparation locale

Installer `requirements.txt`. Les scripts utilisent trois variables d'environnement : `SITE_FTP_HOST`, `SITE_FTP_USER`, `SITE_FTP_PASSWORD`. Aucun identifiant secret n'est enregistré dans les sources.

1. `python scripts/snapshot.py` récupère les ressources publiques.
2. `python scripts/remote_snapshot.py` sauvegarde les pages HTML et styles actuels via SFTP.
3. `python scripts/build.py` construit le dossier local `site/` et la liste exacte des changements.
4. `python scripts/validate.py` contrôle les liens, formulaires, scripts, identifiants et photographies.
5. `python scripts/serve.py` ouvre l'aperçu sur `http://127.0.0.1:8765/`. Les ressources non copiées sont lues sur le site public.

## Publication

`python scripts/deploy.py` vérifie que les fichiers OVH n'ont pas changé depuis la sauvegarde, conserve une copie locale de chaque fichier remplacé, envoie les ressources avant les pages et valide les empreintes des fichiers transférés. Les fichiers sont remplacés par renommage atomique. Un échec déclenche la restauration des fichiers déjà publiés.

Les modifications des pages secondaires concernent uniquement les versions d'URL des feuilles de style communes pour éviter un affichage issu du cache. Les deux accueils reçoivent les changements de structure documentés dans `docs/design.md`.
