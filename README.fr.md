[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **Français**

# schwab-table

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Un Claude Skill qui transforme une liste d'actions, une capture d'écran de positions chez un courtier ou des données de performance/classement déjà prêtes en un tableau de performance dans le style des études de Charles Schwab, produit en chinois et en anglais (PNG + HTML).

![Version anglaise](examples/neural9_en.png)

![Version chinoise](examples/neural9_zh.png)

## Trois modes

| Mode | Entrée | Colonnes 2 à 5 | Exemple |
|---|---|---|---|
| A. Tableau de classement | Le rendement depuis le début de l'année (YTD) de chaque action et son rang dans le S&P 500 / NASDAQ | YTD, rang de performance S&P 500, rang de contribution S&P 500, rang de performance NASDAQ | [EN](examples/neural9_en.png) · [中文](examples/neural9_zh.png) |
| B. Tableau de positions | Une capture d'écran ou un export de positions chez un courtier | Gain/perte latent en %, gain/perte du jour, coût moyen, nombre de titres | [EN](examples/holdings_en.png) · [中文](examples/holdings_zh.png) |
| C. Tableau de liste de suivi | Uniquement des symboles boursiers | YTD, 1 mois, 1 an, dernier cours de clôture | [EN](examples/watchlist_en.png) · [中文](examples/watchlist_zh.png) |

Le mode A utilise les données d'un graphique public de Charles Schwab. Les exemples des modes B et C reposent sur des sociétés fictives et des chiffres inventés, à titre d'illustration uniquement.

## Utilisation avec Claude

Une fois installé, il suffit de demander en langage naturel, par exemple :

- Fais-moi un tableau de performance pour NVDA, AMD et MU.
- Transforme cette capture d'écran de positions en tableau de style Schwab. (joindre la capture)
- Fais un tableau de classement Neural9 2026 à partir de ces données.

## Sources de données

Uniquement des données faisant autorité : cours de clôture officiels des bourses, fournisseurs d'indices (S&P Dow Jones Indices, Nasdaq Global Indexes, éventuellement via FRED), communications aux investisseurs des entreprises et documents déposés à la SEC, ou données de courtier de l'utilisateur. Les rendements sont calculés à partir des cours de clôture officiels ; les variations déjà calculées par des sites agrégateurs ne sont pas utilisées. Les règles détaillées sont dans [SKILL.md](SKILL.md) (en chinois) ; une traduction anglaise est disponible dans [SKILL.en.md](SKILL.en.md).

## Fichiers

- `SKILL.md` : la définition du skill chargée par Claude (structure, paramètres visuels, règles sur les sources de données, liste de contrôle), en chinois
- `SKILL.en.md` : traduction anglaise de `SKILL.md`, pour les lecteurs humains
- `render_table.py` : le moteur de rendu. Il lit une spécification JSON et produit des fichiers HTML en chinois et en anglais ainsi que des PNG en 2x
- `requirements.txt` : dépendance Python (Playwright)
- `examples/` : une spécification et son rendu pour chacun des trois modes
- `assets/` : image d'aperçu social

## Installation

Clonez le dépôt dans le répertoire de skills de Claude :

```bash
git clone https://github.com/imoneys10k/schwab-table.git ~/.claude/skills/schwab-performance-table
```

Ou téléchargez le dossier et importez-le dans les paramètres Skills de claude.ai.

## Rendu manuel

Python 3.9 ou supérieur est requis.

```bash
pip install -r requirements.txt && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

Options : `--langs en` ne rend que les langues indiquées (séparées par des virgules) ; `--no-png` n'écrit que le HTML et ne nécessite pas Playwright. Les dossiers de sortie manquants sont créés automatiquement.

Polices : Inter pour les caractères latins et les chiffres, Noto Sans CJK SC / Source Han Sans SC pour le chinois. À défaut, repli sur Helvetica Neue / PingFang.

## Avertissement

Ce projet ne produit que la mise en forme de tableaux et ne fournit aucun conseil en investissement. Les données des exemples sont données à titre d'illustration uniquement.

## Licence

[MIT](LICENSE)
