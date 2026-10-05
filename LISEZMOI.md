# Site web de Ranko — mode d'emploi

Ce dossier contient tout le site ranko.ca. Il ne dépend plus de Squarespace.
Vous n'avez rien à installer : le site se fabrique avec **Python**, déjà présent sur votre Mac.

---

## 1. Voir le site sur votre ordinateur (aperçu)

1. Ouvrez l'application **Terminal** (Applications → Utilitaires → Terminal).
2. Copiez-collez ces deux lignes, puis appuyez sur Entrée :

   ```
   cd ~/Desktop/ranko-site
   python3 build.py serve
   ```

3. Ouvrez votre navigateur à l'adresse **http://localhost:8080**
4. Pour arrêter l'aperçu : revenez dans le Terminal et appuyez sur **Ctrl + C**.

> Après chaque modification, arrêtez (Ctrl + C) puis relancez `python3 build.py serve`,
> et rechargez la page dans le navigateur.

---

## 2. Où se trouve quoi

| Dossier / fichier | Ce qu'il contient |
|---|---|
| `content/` | **Tous les textes** du site (un fichier par page) |
| `content/projects/` | Un fichier texte par projet (ex. `dior.txt`) |
| `content/work-order.txt` | L'ordre des projets sur la page Work |
| `content/home.txt` | L'accueil : phrases, projets mis en avant, vidéo héro, chiffres |
| `images/` | **Toutes les images**, un dossier par projet |
| `IMAGES.md` | La liste de chaque encart d'image : nom, dimensions, dossier |
| `src/` | Le design (couleurs, typographie, animations). Pas besoin d'y toucher. |
| `dist/` | Le site fabriqué, prêt à mettre en ligne. Ne pas modifier : il est recréé à chaque fois. |

---

## 3. Modifier un texte

Ouvrez le fichier voulu dans `content/` avec **TextEdit** (clic droit → Ouvrir avec → TextEdit).
Si TextEdit affiche une mise en forme, choisissez Format → Convertir au format texte.

Petits codes utilisés dans les textes :

| Vous écrivez | Résultat |
|---|---|
| `## Titre` | un grand titre |
| `### Sous-titre` | un titre plus petit |
| `**mot**` | **gras** |
| `*mot*` | *italique* |
| `[texte](https://adresse.com)` | un lien |
| `- élément` | une liste |

Une ligne vide sépare deux blocs.

---

## 4. Ajouter un projet

1. Dans `content/projects/`, **dupliquez** un projet existant (ex. `dior.txt`)
   et renommez la copie avec le nom court du nouveau projet, en minuscules et sans espace ni accent :
   `nouveau-projet.txt`. Ce nom devient l'adresse de la page : ranko.ca/**nouveau-projet**.
2. Ouvrez-le et remplacez les informations :

   ```
   title: Nom du projet
   role: Ce que Ranko a fait (ex. Motion design & editing)
   page_title: Ranko — Nom du projet — courte description (titre dans Google)
   description: Une ou deux phrases pour Google.
   cover_alt: Description de l'image de couverture (pour l'accessibilité)

   == intro

   Premier paragraphe.

   Deuxième paragraphe.

   == credits

   **CLIENT** — Nom du client
   **AGENCY** — Nom de l'agence
   **SERVICES** — ...
   **TEAM** — ...

   == media

   film 123456789

   video 123456789

   video 123456789 half | video 123456789 half

   ### Une phrase entre deux vidéos.

   image image-01 1600x900 alt="Description de l'image"
   ```

3. Ajoutez le nom court (`nouveau-projet`) dans `content/work-order.txt`, à la place voulue.
4. Déposez la couverture dans `images/nouveau-projet/cover.webp` (1200 × 1500, voir IMAGES.md).
5. Relancez `python3 build.py serve` pour vérifier.

### Les lignes de la section `== media`

| Ligne | Ce que ça affiche |
|---|---|
| `film 123456789` | Une vidéo Vimeo avec un bouton **Play** (le son est possible) |
| `video 123456789` | Une vidéo Vimeo **en boucle, muette**, qui démarre quand elle arrive à l'écran |
| `image image-01 1600x900` | Une image : fichier `images/<projet>/image-01.webp`, format 1600 × 900 |
| `clip image-05 270x480` | Une courte vidéo MP4 muette en boucle hébergée avec le site : `images/<projet>/image-05.mp4` |

- Le numéro Vimeo est celui de l'adresse de la vidéo : vimeo.com/**123456789**.
  Pour une vidéo « non répertoriée », ajoutez le code après une barre : `video 123456789/abc123def0`.
- Taille : ajoutez `half` (moitié), `third` (tiers) ou `quarter` (quart). Sans rien, la vidéo prend toute la largeur.
  Ajoutez `right` pour caler un élément seul à droite.
- Plusieurs éléments sur la même ligne, séparés par ` | `, s'affichent côte à côte.
- Légende sous un élément : `caption="Ep1: Doooo"`.

Le format de chaque nouvelle vidéo est récupéré automatiquement sur Vimeo lors de la fabrication (connexion Internet nécessaire).

---

## 5. Remplacer ou ajouter une image

Tout est expliqué dans **IMAGES.md** (mis à jour automatiquement). En résumé :

1. Exportez l'image en **WebP** (le site gratuit https://squoosh.app le fait très bien).
2. Donnez-lui le nom indiqué et déposez-la dans le bon dossier de `images/`.
3. Relancez la fabrication.

Facultatif : pour les grandes images, une copie de 800 px de large nommée `nom-800.webp`
(ex. `image-01-800.webp`) sera chargée par les téléphones. Le site est plus rapide, mais ça marche aussi sans.

Pour une vidéo, l'image affichée en attendant qu'elle démarre est `images/<projet>/video-<numéro>.webp`.

---

## 6. Changer les projets de l'accueil, la vidéo héro ou les chiffres

Dans `content/home.txt` :

- `featured:` la liste des projets affichés sur l'accueil, dans l'ordre, séparés par des virgules ;
- `reel:` le numéro Vimeo de la vidéo héro (bouton « Play reel ») ;
- `loops:` les deux vidéos en boucle sous la deuxième phrase ;
- `== facts` : les chiffres. `{projects}` et `{brands}` se comptent tout seuls
  (nombre de projets et nombre de marques de la page About).

---

## 7. Enregistrer vos changements (git)

Le dossier garde l'historique de toutes les versions. Après une modification, dans le Terminal :

```
cd ~/Desktop/ranko-site
git add -A
git commit -m "Ce que j'ai changé"
```

---


## Version française (/fr)

Le site existe en anglais (adresse normale, langue d'arrivée) et en français (**/fr** : /fr/work, /fr/dior…).
Le sélecteur **FR / EN** est dans la barre du haut (sur téléphone : dans le menu « + »).

- Les textes français sont dans **`content/fr/`**, même nom et même place que les fichiers anglais. Ils ne contiennent
  **que les textes** : tout ce qui n'y est pas est repris de l'anglais (images, vidéos, mise en page, ordre des projets).
- Dans une section `== media`, n'écrivez que les paragraphes de texte (titres `##`, `###`, phrases), dans le même ordre
  que dans le fichier anglais : ils remplacent les textes anglais un par un. Les lignes `video …`, `image …` restent
  dans le fichier anglais seulement. Si le nombre de textes ne correspond pas, la fabrication du site vous le signale.
- Section `== alt` : la description de chaque image en français (`image-01 = …`).
- Les mots de l'interface (menu, boutons, pied de page, bandeau des témoins) sont dans `build.py`, dictionnaire `FR`.

## Vérification automatique avant publication

À chaque fabrication du site, une vérification s'affiche à la fin :

- ✅ « toutes les images, vidéos, pages et liens du site sont présents » → tout va bien ;
- ⚠️ une liste de problèmes (ex. « Image manquante : images/dior/cover.webp ») → le fichier n'est pas là
  ou son nom ne correspond pas. Corrigez, puis relancez.

Au moment de la mise en ligne, l'hébergeur lance `python3 build.py check` : **s'il manque quoi que ce soit, il refuse
de publier et la version déjà en ligne reste en place.** Vos visiteurs ne voient donc jamais une page avec un trou.

## 8. Mettre le site en ligne

Le site est en ligne sur **https://www.ranko.ca** (depuis le 1er octobre 2026), hébergé gratuitement sur **GitHub Pages**. Le domaine ranko.ca et les courriels Google Workspace
restent chez Squarespace : on ne change que les lignes du *site* dans l'annuaire (DNS), jamais celles des courriels.

### Comment ça marche une fois en ligne

Pour envoyer une nouvelle version : enregistrer les changements (`git commit`), puis lancer `./publish.sh`.
Le script vérifie le site et envoie une copie sans les notes de travail (`SUIVI.md`) ni l'historique.
Dépôt : https://github.com/romain173/romain173.github.io — adresse provisoire : https://romain173.github.io

Chaque fois que la branche `main` est envoyée sur GitHub, GitHub fabrique le site et lance la vérification
(`python3 build.py check`). S'il manque quoi que ce soit, rien n'est publié et la version en ligne reste en place.
Sinon, le site est à jour en une à deux minutes. Réglage : `.github/workflows/deploy.yml`.

### Première mise en ligne (une seule fois)

1. **Sauvegarde** : dans Squarespace → Domaines → ranko.ca → Réglages DNS, faire une capture d'écran de **toute** la page.
2. **GitHub** : créer un compte, puis un dépôt public pour le site ; y envoyer la branche `main`.
3. **GitHub → Settings → Pages** : *Source* = « GitHub Actions » ; *Custom domain* = `www.ranko.ca`.
   Le site est d'abord visible à l'adresse provisoire `<identifiant>.github.io/<dépôt>` pour une dernière vérification.
4. **Squarespace → Réglages DNS**, uniquement les lignes du site :
   - retirer le bloc « Squarespace Defaults » (lignes A vers 198.185.159.x et `www` vers ext-cust.squarespace.com) ;
   - ajouter 4 lignes **A**, nom `@` : 185.199.108.153 · 185.199.109.153 · 185.199.110.153 · 185.199.111.153 ;
   - ajouter 1 ligne **CNAME**, nom `www` → `<identifiant>.github.io`.
   - **Ne jamais toucher** aux blocs « Google Workspace » (MX) et « Google Workspace Verification » (TXT),
     ni aux lignes SPF (`_spf.google.com`), `google._domainkey` et `_dmarc`.
5. Attendre quelques minutes à quelques heures, puis dans GitHub → Pages, cocher **Enforce HTTPS**.
6. **Vérifier** : ranko.ca et www.ranko.ca affichent le nouveau site en https ; les lignes de courriel sont
   identiques à la capture ; envoyer un courriel vers hello@ranko.ca et depuis hello@ranko.ca.
7. **Une semaine plus tard** : annuler dans Squarespace **seulement l'abonnement « site web »**.
   Garder l'abonnement **domaine** (renouvellement le 14 février 2027) et **Google Workspace** (facturé par Squarespace).

### En cas de problème

Remettre les lignes A et `www` de la capture : l'ancien site Squarespace revient tant que son abonnement est actif.

### Bon à savoir

- L'ancienne adresse `/homepage` renvoie vers l'accueil (fichier `src/static/homepage.html`).
- `src/static/CNAME` contient `www.ranko.ca` (le domaine du site pour GitHub).
- Les fichiers `_headers` et `_redirects` ne servent qu'à Cloudflare ou Netlify ; GitHub les ignore.
