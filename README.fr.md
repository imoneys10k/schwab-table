[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **Français**

# schwab-table

Un Claude Skill qui transforme une liste d'actions, une capture d'écran de positions chez un courtier ou des données de performance/classement déjà prêtes en un tableau de performance dans le style des études de Charles Schwab, produit en chinois et en anglais (PNG + HTML).

![Exemple](examples/neural9_en.png)

## Trois modes

| Mode | Entrée | Colonnes 2 à 5 |
|---|---|---|
| A. Tableau de classement | Le rendement depuis le début de l'année (YTD) de chaque action et son rang dans le S&P 500 / NASDAQ | YTD, rang de performance S&P 500, rang de contribution S&P 500, rang de performance NASDAQ |
| B. Tableau de positions | Une capture d'écran ou un export de positions chez un courtier | Gain/perte latent en %, gain/perte du jour, coût moyen, nombre de titres |
| C. Tableau de liste de suivi | Uniquement des symboles boursiers | YTD, 1 mois, 1 an, dernier cours de clôture |

## Sources de données

Uniquement des données faisant autorité : cours de clôture officiels des bourses, fournisseurs d'indices (S&P Dow Jones Indices, Nasdaq Global Indexes, éventuellement via FRED), communications aux investisseurs des entreprises et documents déposés à la SEC, ou données de courtier de l'utilisateur. Les rendements sont calculés à partir des cours de clôture officiels ; les variations déjà calculées par des sites agrégateurs ne sont pas utilisées. Voir [SKILL.md](SKILL.md) pour le détail.

## Fichiers

- `SKILL.md` : la définition du skill (structure, paramètres visuels, règles sur les sources de données, liste de contrôle)
- `render_table.py` : le moteur de rendu. Il lit une spécification JSON et produit des fichiers HTML en chinois et en anglais ainsi que des PNG en 2x
- `examples/` : un exemple du mode A (données issues d'un graphique public de Charles Schwab, au 2/10/2026)

## Installation

Placez ce dossier dans le répertoire de skills de Claude, ou importez-le dans les paramètres Skills de claude.ai.

## Rendu manuel

```bash
pip install playwright && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

Polices : Inter pour les caractères latins et les chiffres, Noto Sans CJK SC / Source Han Sans SC pour le chinois. À défaut, repli sur Helvetica Neue / PingFang.

## Avertissement

Ce projet ne produit que la mise en forme de tableaux et ne fournit aucun conseil en investissement. Les données des exemples sont données à titre d'illustration uniquement.
