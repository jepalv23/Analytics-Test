# Analytics-Test
# CFB Data Pipeline

A Python data pipeline for collecting, cleaning, storing, and analyzing
college football statistics.

The project combines structured college football data with NCAA statistics
to create a normalized dataset suitable for statistical analysis,
visualization, and machine learning.

## Goals

The project is designed to answer questions such as:

- Which teams have the most efficient offenses?
- Which defenses generate the most turnovers?
- How do teams perform against ranked opponents?
- Which players lead the country in passing, rushing, and receiving?
- How do conferences compare?
- How does a team's performance change throughout a season?
- Which statistics correlate most strongly with winning?
- Can historical statistics be used to predict game outcomes?

---

## Data Sources

### NCAA

NCAA statistics are used for official individual and team statistical
categories.

Examples include:

- Passing yards
- Passing touchdowns
- Rushing yards
- Rushing touchdowns
- Receiving yards
- Total offense
- Scoring offense
- Scoring defense
- Turnover margin
- Third-down conversion
- Red-zone offense
- Sacks
- Tackles for loss

The NCAA provides separate individual and team statistical categories
for FBS football.

Source:

https://www.ncaa.com/stats/football/FBS

### College Football Data

College Football Data provides structured data through a REST API.

The API provides:

- Games
- Teams
- Players
- Rosters
- Game statistics
- Season statistics
- Play-by-play
- Rankings
- Recruiting
- Advanced statistics

The API supports historical game data going back to the 19th century,
while team/player statistical coverage is narrower depending on the
dataset.

Source:

https://api.collegefootballdata.com/

An API key is required for protected operations.

The key is supplied through:

    CFBD_API_KEY

and is never committed to the repository.

---

## Architecture

```text
                    DATA SOURCES
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
       NCAA Statistics          CFBD API
            │                         │
            └────────────┬────────────┘
                         │
                         ▼
                  INGESTION LAYER
                         │
                         ▼
                    RAW DATA
                         │
                         ▼
                  TRANSFORMATION
                         │
                         ▼
                  NORMALIZATION
                         │
                         ▼
                    DATABASE
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
           Analysis   Exports    Notebooks
