# PFE Copilot

**PFE Copilot** est une application locale Streamlit qui aide les étudiants à
préparer leurs candidatures de stage de fin d'études (PFE). Elle analyse une
offre, identifie le profil data le plus adapté, sélectionne le CV correspondant,
génère un brouillon d'e-mail et peut enregistrer ou suivre les candidatures.

Le projet prend en charge les candidatures ciblées, les fichiers CSV d'offres,
les e-mails Gmail, les candidatures spontanées et les historiques stockés dans
SQLite.

## Fonctionnalités

- Analyse lexicale du titre et de la description d'une offre.
- Détection de quatre profils : Data Engineer, Data Scientist, BI/Data Analyst
  et AI Engineer.
- Sélection automatique du CV PDF associé dans le dossier `cvs/`.
- Génération d'e-mails de candidature en français ou en anglais.
- Génération personnalisable d'une lettre de motivation au format PDF.
- Import d'offres depuis un fichier CSV.
- Lecture des offres depuis Gmail via l'API Gmail OAuth 2.0.
- Envoi Gmail avec confirmation explicite pour les candidatures spontanées.
- Suivi local des brouillons et candidatures spontanées dans SQLite.

> **Avertissement :** le matching est lexical et repose sur les mots-clés de
> `config/profile.json`. Il ne remplace pas une lecture humaine de l'offre.

## Aperçu des onglets

| Onglet | Usage |
|---|---|
| Nouvelle candidature | Saisir une offre et produire un brouillon |
| Importer des offres | Importer et vérifier un lot d'offres CSV |
| Importer depuis Gmail | Lire les e-mails susceptibles d'être des offres |
| Candidature spontanée | Préparer, joindre les PDF et envoyer via Gmail |
| Suivi des candidatures | Consulter les candidatures enregistrées |

## Architecture technique

- Interface : Streamlit
- Traitement des données : pandas
- Extraction PDF : PyMuPDF
- Génération PDF : ReportLab
- Base de données : SQLite
- Lecture et envoi Gmail : Google Gmail API et OAuth 2.0
- Configuration du candidat et des rôles : JSON

```text
PFE-copilot/
├── app.py                         # Application Streamlit
├── config/
│   └── profile.json               # Profil candidat et mots-clés
├── cvs/                           # CV PDF par profil
├── data/                          # Bases SQLite et données d'import
├── src/
│   ├── cv_selector.py
│   ├── database.py
│   ├── gmail_reader.py
│   ├── gmail_sender.py
│   └── ...
├── templates/                     # Modèles d'e-mails
├── tests/                         # Tests pytest
├── .env.example
└── requirements.txt
```

## Prérequis

- Python 3.10 ou supérieur
- `pip` et `venv`
- Git
- Un navigateur web
- Pour Gmail : un compte Google et un projet Google Cloud

## Installation locale

### 1. Cloner le dépôt

```bash
git clone https://github.com/ghassouine19/PFE-copilot.git
cd PFE-copilot
```

### 2. Créer un environnement virtuel

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Si PowerShell bloque l'activation du script :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3. Installer les dépendances

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Préparer la configuration locale

```bash
cp .env.example .env
```

Sous Windows, utilisez plutôt :

```powershell
Copy-Item .env.example .env
```

Le fichier `.env` est ignoré par Git. Pour l'instant, les chemins importants sont
gérés directement par le code ; les variables présentes dans `.env.example`
documentent la configuration locale prévue.

## Lancer l'application

Depuis la racine du projet :

```bash
streamlit run app.py
```

Ouvrez ensuite l'adresse affichée dans le terminal, généralement
`http://localhost:8501`.

Au premier lancement, les bases SQLite suivantes sont créées automatiquement
dans `data/` :

- `pfe_copilot.db`
- `spontaneous_applications.db`

Elles sont locales et ignorées par Git.

## Utilisation sans Gmail

PFE Copilot peut être utilisé sans configuration Gmail :

1. Sélectionnez l'onglet **Nouvelle candidature**.
2. Renseignez l'entreprise, le poste et la description.
3. Lancez l'analyse.
4. Vérifiez le score, le profil détecté et les mots-clés.
5. Modifiez éventuellement l'objet ou le corps de l'e-mail.
6. Cliquez sur **Enregistrer le brouillon** pour le conserver dans SQLite.

Les CV disponibles peuvent être remplacés ou ajoutés dans `cvs/`. Les chemins
sont définis dans `config/profile.json`.

## Importer des offres depuis un CSV

Dans l'onglet **Importer des offres**, fournissez un CSV encodé en UTF-8 avec
au minimum ces colonnes :

```csv
company,title,description,recipient,source_url
Tech Maroc,Data Engineer PFE,Python SQL Spark et Big Data,rh@entreprise.ma,https://example.com/offre
```

Les colonnes `recipient` et `source_url` sont facultatives. Les colonnes
obligatoires sont `company`, `title` et `description`.

## Configurer Gmail

La lecture et l'envoi Gmail sont facultatifs. Les identifiants OAuth ne doivent
jamais être partagés ou ajoutés au dépôt.

### 1. Créer les identifiants Google

1. Connectez-vous à [Google Cloud Console](https://console.cloud.google.com/).
2. Créez un nouveau projet.
3. Ouvrez **APIs & Services > Library**.
4. Activez **Gmail API**.
5. Ouvrez **APIs & Services > OAuth consent screen**.
6. Configurez l'écran de consentement pour un usage externe ou interne.
7. Ajoutez votre compte Google à la liste des utilisateurs test si l'application
   est en phase de test.
8. Ouvrez **APIs & Services > Credentials**.
9. Cliquez sur **Create credentials > OAuth client ID**.
10. Choisissez **Desktop app**.
11. Téléchargez le fichier JSON.

### 2. Installer les identifiants

Placez le fichier téléchargé à la racine du projet sous le nom exact
`credentials.json` :

```text
PFE-copilot/
├── app.py
├── credentials.json
└── ...
```

Le fichier `credentials.json` et le jeton `token.json` généré après autorisation
sont tous deux ignorés par Git.

### 3. Autoriser l'application

Vous pouvez tester la connexion depuis un terminal :

```bash
python test_gmail_connection.py
```

Lors du premier appel à Gmail, une fenêtre de navigateur s'ouvre pour demander
les autorisations suivantes :

- Lire les e-mails ;
- Envoyer des e-mails au nom du compte connecté.

Après autorisation, le jeton est enregistré dans `token.json`. Les autorisations
suivantes sont généralement renouvelées automatiquement.

Vous pouvez aussi ouvrir l'onglet **Importer depuis Gmail** puis cliquer sur
**Récupérer les e-mails Gmail**. Cette fonctionnalité recherche les e-mails
récents issus de l'année précédente contenant des expressions liées aux PFE.

### 4. Envoyer une candidature spontanée

Dans **Candidature spontanée** :

1. Saisissez l'adresse RH.
2. Choisissez le profil ciblé.
3. Ajoutez l'entreprise et votre nom si nécessaire.
4. Sélectionnez la langue.
5. Vérifiez l'e-mail, le CV et la lettre générée.
6. Cochez la confirmation explicite.
7. Cliquez sur **Envoyer la candidature via Gmail**.

L'e-mail joint automatiquement le CV PDF correspondant et la lettre de
motivation générée en PDF.

## Personnalisation

### Modifier le profil candidat

Modifiez `config/profile.json` pour changer :

- le diplôme et la localisation ;
- les langues ;
- les rôles reconnus ;
- les mots-clés du matching ;
- les chemins des CV PDF.

### Modifier les CV

Chaque fichier du dossier `cvs/` doit rester associé au chemin déclaré dans
`config/profile.json`. Les quatre profils attendus sont :

- `cvs/data_engineer.pdf`
- `cvs/data_scientist.pdf`
- `cvs/bi_analyst.pdf`
- `cvs/ai_engineer.pdf`

## Exécuter les tests

Le dépôt contient les futurs emplacements `tests/test_matcher.py` et
`tests/test_cv_selector.py`. Ils sont actuellement vides.

Pour lancer une suite pytest lorsque des tests y seront ajoutés :

```bash
python -m pip install pytest
python -m pytest -q tests
```

Le script `test_gmail_connection.py` est un test de connexion manuel et non une
suite pytest. Utilisez plutôt :

```bash
python test_gmail_connection.py
```

## Réinitialiser les données locales

Pour supprimer toutes les données locales SQLite :

**Linux/macOS**

```bash
rm -f data/pfe_copilot.db data/spontaneous_applications.db
```

**Windows (PowerShell)**

```powershell
Remove-Item data/pfe_copilot.db, data/spontaneous_applications.db -ErrorAction SilentlyContinue
```

Les bases sont recréées automatiquement au prochain démarrage de l'application.

Pour supprimer aussi l'autorisation Gmail locale :

```bash
rm -f token.json
```

Sous Windows :

```powershell
Remove-Item token.json -ErrorAction SilentlyContinue
```

## Sécurité et bonnes pratiques

- Ne publiez jamais `credentials.json`, `token.json` ou des données sensibles.
- Vérifiez toujours le destinataire, l'objet et le contenu avant un envoi.
- Ne confondez pas les fichiers `.env` locaux avec des identifiants OAuth.
- Testez avec un compte Gmail secondaire si nécessaire.
- Sauvegardez les CV avant toute modification.

## Dépannage

### `streamlit: command not found`

L'environnement virtuel n'est pas activé ou les dépendances ne sont pas
installées :

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Sous Windows, remplacez `source .venv/bin/activate` par
`.venv\Scripts\Activate.ps1`.

### `Ajoute credentials.json à la racine du projet`

Téléchargez un identifiant OAuth de type **Desktop app** depuis Google Cloud,
puis placez-le à la racine sous le nom `credentials.json`.

### Erreur d'envoi Gmail

Vérifiez que :

- Gmail API est activée ;
- l'adresse utilisée est ajoutée aux utilisateurs test ;
- `token.json` n'est pas obsolète ;
- l'adresse RH saisie est valide ;
- le CV cible existe au format PDF.

Pour renouveler entièrement l'autorisation Gmail :

```bash
rm -f token.json
python test_gmail_connection.py
```

Sous Windows :

```powershell
Remove-Item token.json -ErrorAction SilentlyContinue
python test_gmail_connection.py
```

### Module ou dépendance introuvable

Relancez l'installation dans l'environnement actif :

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Licence

Ce projet est actuellement fourni pour un usage académique et personnel.