from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterator

import pandas as pd
import requests
from bs4 import BeautifulSoup

from cfb_pipeline.utils.parsing import (
    clean_integer,
    clean_percentage,
    normalize_team_name,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TeamStatistic:
    season: int
    team: str
    category: str
    rank: int | None
    value: float | None


class NCAATeamStatsScraper:
    """
    Scrapes NCAA FBS team statistics and converts the source
    HTML tables into normalized TeamStatistic objects.

    The scraper intentionally keeps source-specific parsing logic
    isolated from the rest of the application.
    """

    BASE_URL = "https://www.ncaa.com/stats/football/fbs"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36"
        )
    }

    STATISTIC_URLS = {
        "scoring_offense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/27"
        ),
        "total_offense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/21"
        ),
        "rushing_offense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/23"
        ),
        "passing_offense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/24"
        ),
        "scoring_defense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/28"
        ),
        "total_defense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/22"
        ),
        "rushing_defense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/25"
        ),
        "passing_defense": (
            "https://www.ncaa.com/stats/football/fbs/current/team/26"
        ),
    }

    def __init__(
        self,
        session: requests.Session | None = None,
        request_delay: float = 1.0,
        timeout: int = 30,
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

        self.request_delay = request_delay
        self.timeout = timeout

    def scrape_season(self, season: int) -> list[TeamStatistic]:
        """
        Scrape all configured team statistics for a season.

        Returns:
            A normalized list of TeamStatistic objects.
        """

        if season < 2000:
            raise ValueError("Only seasons from 2000 onward are supported.")

        results: list[TeamStatistic] = []

        for category, url in self.STATISTIC_URLS.items():
            logger.info(
                "Scraping NCAA statistic category=%s season=%s",
                category,
                season,
            )

            try:
                html = self._download_page(url, season)
                statistics = self._parse_table(
                    html=html,
                    season=season,
                    category=category,
                )

                results.extend(statistics)

            except Exception:
                logger.exception(
                    "Failed to scrape category=%s season=%s",
                    category,
                    season,
                )

            time.sleep(self.request_delay)

        logger.info(
            "Finished NCAA team statistics season=%s records=%d",
            season,
            len(results),
        )

        return results

    def _download_page(self, url: str, season: int) -> str:
        response = self.session.get(
            url,
            params={
                "season": season,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        if not response.text.strip():
            raise RuntimeError(
                f"NCAA returned an empty response for {url}"
            )

        return response.text

    def _parse_table(
        self,
        html: str,
        season: int,
        category: str,
    ) -> list[TeamStatistic]:
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")

        if table is None:
            raise RuntimeError(
                f"Could not find statistics table for {category}"
            )

        rows = table.find_all("tr")

        if not rows:
            return []

        headers = self._extract_headers(rows[0])

        if not headers:
            raise RuntimeError(
                f"Could not determine table headers for {category}"
            )

        statistics: list[TeamStatistic] = []

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])

            if not cells:
                continue

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            record = self._parse_row(
                values=values,
                headers=headers,
                season=season,
                category=category,
            )

            if record is not None:
                statistics.append(record)

        return statistics

    @staticmethod
    def _extract_headers(row) -> list[str]:
        headers = []

        for cell in row.find_all(["th", "td"]):
            value = cell.get_text(" ", strip=True)

            if value:
                headers.append(value.lower())

        return headers

    def _parse_row(
        self,
        values: list[str],
        headers: list[str],
        season: int,
        category: str,
    ) -> TeamStatistic | None:
        if len(values) < 2:
            return None

        if len(values) != len(headers):
            logger.warning(
                "Column mismatch category=%s headers=%d values=%d",
                category,
                len(headers),
                len(values),
            )

        rank = None
        team = None
        value = None

        for index, header in enumerate(headers):
            if index >= len(values):
                continue

            raw_value = values[index]

            if header in {"rank", "rk", "ranking"}:
                rank = clean_integer(raw_value)

            elif header in {"team", "school", "team name"}:
                team = normalize_team_name(raw_value)

            elif header in {
                "value",
                "avg",
                "average",
                "yards",
                "points",
            }:
                value = clean_percentage(raw_value)

        if team is None:
            team = normalize_team_name(values[1])

        if not team:
            return None

        if value is None:
            value = self._find_numeric_value(values)

        return TeamStatistic(
            season=season,
            team=team,
            category=category,
            rank=rank,
            value=value,
        )

    @staticmethod
    def _find_numeric_value(values: list[str]) -> float | None:
        for value in reversed(values):
            cleaned = value.replace(",", "").strip()

            try:
                return float(cleaned)
            except ValueError:
                continue

        return None

    def iter_seasons(
        self,
        start_year: int,
        end_year: int,
    ) -> Iterator[TeamStatistic]:
        """
        Stream statistics across multiple seasons.

        This avoids keeping every season in memory at once.
        """

        if end_year < start_year:
            raise ValueError("end_year must be >= start_year")

        for season in range(start_year, end_year + 1):
            statistics = self.scrape_season(season)

            for statistic in statistics:
                yield statistic
