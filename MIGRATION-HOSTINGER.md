# Migration GitHub Pages → Hostinger / hymeria.com

Checklist pas-à-pas pour basculer le site en production sur **www.hymeria.com**.

---

## 🅰️ La veille (préparation locale, sans rien casser)

### Côté Claude / repo
- [ ] Lancer le script de bascule des URLs :
  ```bash
  cd ~/Desktop/HYMERIA/hymeria-site
  python3 scripts/swap_domain.py
  ```
  → met à jour canonical, hreflang, og:url, twitter:image, JSON-LD `@id`, sitemap.xml, robots.txt vers `https://www.hymeria.com`.

- [ ] Vérifier qu'il ne reste plus de `laetitiaperson.github.io` dans le HTML/XML :
  ```bash
  grep -rn 'laetitiaperson.github.io' --include='*.html' --include='*.xml' --include='*.txt' .
  ```
  Doit retourner **0 résultat**.

- [ ] Commit + push de la branche prod (NE PAS encore pousser sur `main` qui sert GitHub Pages) :
  ```bash
  git checkout -b prod-hostinger
  git commit -am "prod: switch URLs to www.hymeria.com"
  git push -u origin prod-hostinger
  ```

### Côté toi (Hostinger)
- [ ] Acheter / activer le hosting Hostinger (si pas fait)
- [ ] Pointer le domaine `www.hymeria.com` vers le serveur Hostinger (DNS A / CNAME)
- [ ] Activer **HTTPS / SSL gratuit (Let's Encrypt)** dans le panel Hostinger
- [ ] Vérifier que tu as accès au **File Manager** ou **FTP**

---

## 🅱️ Le jour J — Upload Hostinger

1. **Préparer le ZIP** depuis ton Desktop :
   ```bash
   cd ~/Desktop/HYMERIA
   zip -r hymeria-site.zip hymeria-site -x '*.git*' -x '*.DS_Store' -x 'scripts/*' -x 'MIGRATION-HOSTINGER.md'
   ```

2. **Uploader** `hymeria-site.zip` dans le dossier `public_html/` de Hostinger via File Manager.

3. **Décompresser** sur Hostinger → tous les fichiers à la racine de `public_html/`.

4. **Vérifier le `.htaccess`** est bien à la racine (`public_html/.htaccess`). S'il n'est pas visible, activer "Show hidden files" dans le File Manager.

5. **Tester** : ouvrir `https://www.hymeria.com` → la home doit charger l'index-fr.html.

---

## 🅲 Le jour J — Côté GitHub (basculer le trafic restant)

- [ ] Sur la branche `main`, ajouter un **redirect HTML** sur chaque page principale du staging, pour rediriger vers la page équivalente sur hymeria.com.
  Exemple à coller dans `<head>` :
  ```html
  <meta http-equiv="refresh" content="0; url=https://www.hymeria.com/">
  <link rel="canonical" href="https://www.hymeria.com/">
  ```
  Mieux encore : remplacer `index-fr.html` par un fichier qui ne fait que rediriger.

- [ ] Optionnel : désactiver complètement GitHub Pages dans **Settings → Pages → Source: None** une fois la nouvelle prod stable.

---

## 🅳 Le jour J — Tests post-déploiement

Sur `https://www.hymeria.com` :

- [ ] Page d'accueil charge sans erreur (visuels, polices Montserrat/Poppins, hero image OK)
- [ ] Hard-reload (Cmd+Shift+R) : pas de FOUT (flash of unstyled text)
- [ ] Menu hamburger fonctionne en < 768px
- [ ] Anchors `#approche`, `#offres`, `#diagnostic` scrollent correctement (titre non coupé)
- [ ] Formulaire de contact : envoyer un test → email reçu sur `contact@hymeria.com`
- [ ] Pages légales accessibles (`/mentions-legales.html`, `/cgu.html`, `/politique-confidentialite.html`)
- [ ] Articles insights accessibles (`/insights/...`)
- [ ] 404 personnalisée s'affiche pour une URL inexistante (`/foo`)
- [ ] Headers HTTP : ouvrir DevTools Network sur un `.woff2` et vérifier `Cache-Control: public, max-age=31536000, immutable`

---

## 🅴 Côté Formspree (5 min)

- [ ] Aller sur [formspree.io](https://formspree.io) → form `mqevkbql` → **Settings → Allowed Domains**
- [ ] Ajouter : `www.hymeria.com` et `hymeria.com`
- [ ] Renvoyer un test depuis le formulaire de contact pour valider

---

## 🅵 Côté Google Search Console (10 min)

1. Aller sur [search.google.com/search-console](https://search.google.com/search-console)
2. **Add Property** → "Domain" → entrer `hymeria.com`
3. Vérifier via DNS (TXT record) — Hostinger gère ça en 1 clic
4. **Sitemaps** → ajouter `https://www.hymeria.com/sitemap.xml`
5. **URL Inspection** → tester `https://www.hymeria.com/index-fr.html` → demander l'indexation
6. **Removals** (optionnel) : demander la dé-indexation de `laetitiaperson.github.io/hymeria-site/` pour éviter les duplicates pendant la transition

---

## 🅶 Suivi (semaines suivantes)

- [ ] Vérifier dans Search Console que `www.hymeria.com` apparaît dans **Coverage > Indexed**
- [ ] Vérifier dans PageSpeed Insights que le score mobile est passé à **90+** grâce aux cache headers
- [ ] Soumettre au moins une URL à l'inspection pour forcer le re-crawl

---

## En cas de problème

- Pour **revenir en arrière sur les URLs** (annuler le swap) :
  ```bash
  python3 scripts/swap_domain.py --revert
  ```

- Pour **rollback Hostinger** : restaurer la version précédente via File Manager (sauvegarde quotidienne incluse dans le plan Hostinger Business+).
