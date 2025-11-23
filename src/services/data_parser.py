"""Data parser for TMDB API responses."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import (
    Movie, MovieCast, MovieCrew, MovieWatchProvider, MovieTranslation,
    SimilarMovie, ExternalIdMovie,
    TVSeries, TVSeriesCast, TVSeriesCrew, TVSeriesCreator,
    TVSeason, TVEpisodeInfo, TVSeriesWatchProvider, TVSeriesTranslation,
    SimilarTVSeries, ExternalIdTVSeries,
    Genre, ProductionCompany, ProductionCountry, SpokenLanguage,
    Keyword, WatchProvider, TVNetwork, Person
)
from ..utils import safe_get, parse_date, setup_logger
from ..config import config


logger = setup_logger(__name__, config.LOGS_DIR / "parser.log", config.LOG_LEVEL)


class DataParser:
    """Parser for TMDB API responses."""

    def __init__(self, db: Session):
        """Initialize parser with database session."""
        self.db = db

    def _get_or_create_genre(self, genre_data: Dict[str, Any]) -> Genre:
        """Get or create genre."""
        genre = self.db.query(Genre).filter_by(id=genre_data["id"]).first()
        if not genre:
            genre = Genre(id=genre_data["id"], name=genre_data["name"])
            self.db.add(genre)
            self.db.flush()
        return genre

    def _get_or_create_company(self, company_data: Dict[str, Any]) -> ProductionCompany:
        """Get or create production company."""
        company = self.db.query(ProductionCompany).filter_by(id=company_data["id"]).first()
        if not company:
            company = ProductionCompany(
                id=company_data["id"],
                name=company_data["name"],
                logo_path=company_data.get("logo_path"),
                origin_country=company_data.get("origin_country")
            )
            self.db.add(company)
            self.db.flush()
        return company

    def _get_or_create_country(self, country_code: str, country_name: str) -> ProductionCountry:
        """Get or create production country."""
        country = self.db.query(ProductionCountry).filter_by(iso_3166_1=country_code).first()
        if not country:
            country = ProductionCountry(iso_3166_1=country_code, name=country_name)
            self.db.add(country)
            self.db.flush()
        return country

    def _get_or_create_language(self, lang_data: Dict[str, Any]) -> SpokenLanguage:
        """Get or create spoken language."""
        language = self.db.query(SpokenLanguage).filter_by(iso_639_1=lang_data["iso_639_1"]).first()
        if not language:
            language = SpokenLanguage(
                iso_639_1=lang_data["iso_639_1"],
                english_name=lang_data.get("english_name"),
                name=lang_data.get("name")
            )
            self.db.add(language)
            self.db.flush()
        return language

    def _get_or_create_keyword(self, keyword_data: Dict[str, Any]) -> Keyword:
        """Get or create keyword."""
        keyword = self.db.query(Keyword).filter_by(id=keyword_data["id"]).first()
        if not keyword:
            keyword = Keyword(id=keyword_data["id"], name=keyword_data["name"])
            self.db.add(keyword)
            # Flush immediately to ensure keyword exists before junction table insert
            self.db.flush()
        return keyword

    def _get_or_create_provider(self, provider_data: Dict[str, Any]) -> WatchProvider:
        """Get or create watch provider."""
        provider = self.db.query(WatchProvider).filter_by(id=provider_data["provider_id"]).first()
        if not provider:
            provider = WatchProvider(
                id=provider_data["provider_id"],
                provider_name=provider_data["provider_name"],
                logo_path=provider_data.get("logo_path"),
                display_priority=provider_data.get("display_priority")
            )
            self.db.add(provider)
            # Flush immediately to avoid duplicate key errors
            self.db.flush()
        return provider

    def _get_or_create_network(self, network_data: Dict[str, Any]) -> TVNetwork:
        """Get or create TV network."""
        network = self.db.query(TVNetwork).filter_by(id=network_data["id"]).first()
        if not network:
            network = TVNetwork(
                id=network_data["id"],
                name=network_data["name"],
                logo_path=network_data.get("logo_path"),
                origin_country=network_data.get("origin_country")
            )
            self.db.add(network)
            self.db.flush()
        return network

    def _get_or_create_person(self, person_data: Dict[str, Any]) -> Person:
        """Get or create person."""
        person = self.db.query(Person).filter_by(id=person_data["id"]).first()
        if not person:
            person = Person(
                id=person_data["id"],
                name=person_data.get("name", ""),
                original_name=person_data.get("original_name"),
                gender=person_data.get("gender"),
                adult=person_data.get("adult", False),
                known_for_department=person_data.get("known_for_department"),
                popularity=person_data.get("popularity"),
                profile_path=person_data.get("profile_path")
            )
            self.db.add(person)
            # Flush immediately to avoid duplicate key errors when the same person appears multiple times
            self.db.flush()
        else:
            # Update person data if it already exists
            person.name = person_data.get("name", "")
            person.original_name = person_data.get("original_name")
            person.gender = person_data.get("gender")
            person.adult = person_data.get("adult", False)
            person.known_for_department = person_data.get("known_for_department")
            person.popularity = person_data.get("popularity")
            person.profile_path = person_data.get("profile_path")
        return person

    def parse_movie(self, data: Dict[str, Any]) -> Movie:
        """Parse movie data from API response."""
        # Get or create movie
        movie = self.db.query(Movie).filter_by(id=data["id"]).first()
        if not movie:
            movie = Movie(id=data["id"])
            self.db.add(movie)

        # Update basic fields
        movie.imdb_id = data.get("imdb_id")
        movie.title = data["title"]
        movie.original_title = data.get("original_title")
        movie.original_language = data.get("original_language")
        movie.overview = data.get("overview")
        movie.tagline = data.get("tagline")
        movie.status = data.get("status")
        movie.adult = data.get("adult", False)
        movie.video = data.get("video", False)
        movie.homepage = data.get("homepage")
        movie.budget = data.get("budget", 0)
        movie.revenue = data.get("revenue", 0)
        movie.runtime = data.get("runtime")
        movie.release_date = parse_date(data.get("release_date"))
        movie.popularity = data.get("popularity")
        movie.vote_average = data.get("vote_average")
        movie.vote_count = data.get("vote_count")
        movie.poster_path = data.get("poster_path")
        movie.backdrop_path = data.get("backdrop_path")
        movie.updated_at = datetime.utcnow()

        # Genres
        movie.genres.clear()
        for genre_data in data.get("genres", []):
            genre = self._get_or_create_genre(genre_data)
            movie.genres.append(genre)

        # Production companies
        movie.production_companies.clear()
        for company_data in data.get("production_companies", []):
            company = self._get_or_create_company(company_data)
            movie.production_companies.append(company)

        # Production countries
        for country_data in data.get("production_countries", []):
            self._get_or_create_country(
                country_data["iso_3166_1"],
                country_data["name"]
            )

        # Spoken languages
        for lang_data in data.get("spoken_languages", []):
            self._get_or_create_language(lang_data)

        # Credits
        self._parse_movie_credits(movie, data.get("credits", {}))

        # Flush to get the movie ID before inserting into junction tables and related records
        self.db.flush()

        # External IDs (requires movie.id to be set)
        self._parse_movie_external_ids(movie, data.get("external_ids", {}))

        # Keywords (requires movie.id to be set)
        self._parse_movie_keywords(movie, data.get("keywords", {}))

        # Watch providers
        self._parse_movie_watch_providers(movie, data.get("watch/providers", {}))

        # Translations
        self._parse_movie_translations(movie, data.get("translations", {}))

        # Similar movies
        self._parse_similar_movies(movie, data.get("similar", {}))

        self.db.flush()
        return movie

    def _parse_movie_credits(self, movie: Movie, credits_data: Dict[str, Any]):
        """Parse movie credits (cast and crew)."""
        # Clear existing
        self.db.query(MovieCast).filter_by(movie_id=movie.id).delete()
        self.db.query(MovieCrew).filter_by(movie_id=movie.id).delete()

        # Cast
        for cast_data in credits_data.get("cast", [])[:50]:  # Limit to top 50
            person = self._get_or_create_person(cast_data)
            cast = MovieCast(
                movie_id=movie.id,
                person_id=person.id,
                character=cast_data.get("character"),
                credit_id=cast_data.get("credit_id"),
                cast_order=cast_data.get("order")
            )
            self.db.add(cast)

        # Crew
        for crew_data in credits_data.get("crew", [])[:100]:  # Limit to top 100
            person = self._get_or_create_person(crew_data)
            crew = MovieCrew(
                movie_id=movie.id,
                person_id=person.id,
                department=crew_data.get("department"),
                job=crew_data.get("job"),
                credit_id=crew_data.get("credit_id")
            )
            self.db.add(crew)

    def _parse_movie_external_ids(self, movie: Movie, external_ids: Dict[str, Any]):
        """Parse movie external IDs."""
        if not external_ids:
            return

        ext_id = self.db.query(ExternalIdMovie).filter_by(movie_id=movie.id).first()
        if not ext_id:
            ext_id = ExternalIdMovie(movie_id=movie.id)
            self.db.add(ext_id)

        ext_id.imdb_id = external_ids.get("imdb_id")
        ext_id.wikidata_id = external_ids.get("wikidata_id")
        ext_id.facebook_id = external_ids.get("facebook_id")
        ext_id.instagram_id = external_ids.get("instagram_id")
        ext_id.twitter_id = external_ids.get("twitter_id")

    def _parse_movie_keywords(self, movie: Movie, keywords_data: Dict[str, Any]):
        """Parse movie keywords."""
        # Clear existing associations
        self.db.execute(
            text("DELETE FROM movie_keywords WHERE movie_id = :movie_id"),
            {"movie_id": movie.id}
        )

        for keyword_data in keywords_data.get("keywords", []):
            keyword = self._get_or_create_keyword(keyword_data)
            self.db.execute(
                text("INSERT INTO movie_keywords (movie_id, keyword_id) VALUES (:movie_id, :keyword_id) ON CONFLICT DO NOTHING"),
                {"movie_id": movie.id, "keyword_id": keyword.id}
            )

    def _parse_movie_watch_providers(self, movie: Movie, providers_data: Dict[str, Any]):
        """Parse movie watch providers."""
        # Clear existing
        self.db.query(MovieWatchProvider).filter_by(movie_id=movie.id).delete()

        for country, data in providers_data.get("results", {}).items():
            for provider_type in ["flatrate", "buy", "rent", "ads", "free"]:
                for provider_data in data.get(provider_type, []):
                    provider = self._get_or_create_provider(provider_data)
                    watch_provider = MovieWatchProvider(
                        movie_id=movie.id,
                        provider_id=provider.id,
                        country_code=country,
                        type=provider_type
                    )
                    self.db.add(watch_provider)

    def _parse_movie_translations(self, movie: Movie, translations_data: Dict[str, Any]):
        """Parse movie translations."""
        # Clear existing
        self.db.query(MovieTranslation).filter_by(movie_id=movie.id).delete()

        for trans_data in translations_data.get("translations", []):
            data = trans_data.get("data", {})
            translation = MovieTranslation(
                movie_id=movie.id,
                iso_639_1=trans_data.get("iso_639_1", ""),
                iso_3166_1=trans_data.get("iso_3166_1", ""),
                name=data.get("name"),
                title=data.get("title"),
                overview=data.get("overview"),
                homepage=data.get("homepage"),
                tagline=data.get("tagline")
            )
            self.db.add(translation)

    def _parse_similar_movies(self, movie: Movie, similar_data: Dict[str, Any]):
        """Parse similar movies."""
        # Clear existing
        self.db.query(SimilarMovie).filter_by(movie_id=movie.id).delete()

        for similar in similar_data.get("results", [])[:20]:  # Limit to 20
            similar_movie = SimilarMovie(
                movie_id=movie.id,
                similar_movie_id=similar["id"]
            )
            self.db.add(similar_movie)

    def parse_tv_series(self, data: Dict[str, Any]) -> TVSeries:
        """Parse TV series data from API response."""
        # Get or create TV series
        tv_series = self.db.query(TVSeries).filter_by(id=data["id"]).first()
        if not tv_series:
            tv_series = TVSeries(id=data["id"])
            self.db.add(tv_series)

        # Update basic fields
        tv_series.name = data["name"]
        tv_series.original_name = data.get("original_name")
        tv_series.original_language = data.get("original_language")
        tv_series.overview = data.get("overview")
        tv_series.tagline = data.get("tagline")
        tv_series.status = data.get("status")
        tv_series.type = data.get("type")
        tv_series.adult = data.get("adult", False)
        tv_series.homepage = data.get("homepage")
        tv_series.in_production = data.get("in_production", False)
        tv_series.first_air_date = parse_date(data.get("first_air_date"))
        tv_series.last_air_date = parse_date(data.get("last_air_date"))
        tv_series.number_of_episodes = data.get("number_of_episodes")
        tv_series.number_of_seasons = data.get("number_of_seasons")
        tv_series.popularity = data.get("popularity")
        tv_series.vote_average = data.get("vote_average")
        tv_series.vote_count = data.get("vote_count")
        tv_series.poster_path = data.get("poster_path")
        tv_series.backdrop_path = data.get("backdrop_path")
        tv_series.updated_at = datetime.utcnow()

        # Genres
        tv_series.genres.clear()
        for genre_data in data.get("genres", []):
            genre = self._get_or_create_genre(genre_data)
            tv_series.genres.append(genre)

        # Production companies
        tv_series.production_companies.clear()
        for company_data in data.get("production_companies", []):
            company = self._get_or_create_company(company_data)
            tv_series.production_companies.append(company)

        # Networks
        tv_series.networks.clear()
        for network_data in data.get("networks", []):
            network = self._get_or_create_network(network_data)
            tv_series.networks.append(network)

        # Creators
        self._parse_tv_creators(tv_series, data.get("created_by", []))

        # Seasons
        self._parse_tv_seasons(tv_series, data.get("seasons", []))

        # Credits
        self._parse_tv_credits(tv_series, data.get("credits", {}))

        # Flush to get the TV series ID before inserting into junction tables and related records
        self.db.flush()

        # Episode info (requires tv_series.id to be set)
        self._parse_tv_episode_info(tv_series, data)

        # External IDs (requires tv_series.id to be set)
        self._parse_tv_external_ids(tv_series, data.get("external_ids", {}))


        # Keywords (requires tv_series.id to be set)
        self._parse_tv_keywords(tv_series, data.get("keywords", {}))

        # Watch providers
        self._parse_tv_watch_providers(tv_series, data.get("watch/providers", {}))

        # Translations
        self._parse_tv_translations(tv_series, data.get("translations", {}))

        # Similar TV series
        self._parse_similar_tv_series(tv_series, data.get("similar", {}))

        self.db.flush()
        return tv_series

    def _parse_tv_creators(self, tv_series: TVSeries, creators_data: List[Dict[str, Any]]):
        """Parse TV series creators."""
        # Clear existing
        self.db.query(TVSeriesCreator).filter_by(tv_series_id=tv_series.id).delete()

        for creator_data in creators_data:
            person = self._get_or_create_person(creator_data)
            creator = TVSeriesCreator(
                tv_series_id=tv_series.id,
                person_id=person.id,
                credit_id=creator_data.get("credit_id")
            )
            self.db.add(creator)

    def _parse_tv_seasons(self, tv_series: TVSeries, seasons_data: List[Dict[str, Any]]):
        """Parse TV seasons."""
        # Clear existing
        self.db.query(TVSeason).filter_by(tv_series_id=tv_series.id).delete()

        for season_data in seasons_data:
            season = TVSeason(
                id=season_data.get("id"),
                tv_series_id=tv_series.id,
                season_number=season_data.get("season_number"),
                name=season_data.get("name"),
                overview=season_data.get("overview"),
                air_date=parse_date(season_data.get("air_date")),
                episode_count=season_data.get("episode_count"),
                poster_path=season_data.get("poster_path"),
                vote_average=season_data.get("vote_average")
            )
            self.db.add(season)

    def _parse_tv_episode_info(self, tv_series: TVSeries, data: Dict[str, Any]):
        """Parse last and next episode to air."""
        # Clear existing
        self.db.query(TVEpisodeInfo).filter_by(tv_series_id=tv_series.id).delete()

        for episode_type in ["last_episode_to_air", "next_episode_to_air"]:
            episode_data = data.get(episode_type)
            if episode_data:
                episode = TVEpisodeInfo(
                    id=episode_data.get("id"),
                    tv_series_id=tv_series.id,
                    episode_type=episode_type,
                    season_number=episode_data.get("season_number"),
                    episode_number=episode_data.get("episode_number"),
                    name=episode_data.get("name"),
                    overview=episode_data.get("overview"),
                    air_date=parse_date(episode_data.get("air_date")),
                    runtime=episode_data.get("runtime"),
                    vote_average=episode_data.get("vote_average"),
                    vote_count=episode_data.get("vote_count"),
                    production_code=episode_data.get("production_code"),
                    still_path=episode_data.get("still_path")
                )
                self.db.add(episode)

    def _parse_tv_credits(self, tv_series: TVSeries, credits_data: Dict[str, Any]):
        """Parse TV series credits."""
        # Clear existing
        self.db.query(TVSeriesCast).filter_by(tv_series_id=tv_series.id).delete()
        self.db.query(TVSeriesCrew).filter_by(tv_series_id=tv_series.id).delete()

        # Cast
        for cast_data in credits_data.get("cast", [])[:50]:
            person = self._get_or_create_person(cast_data)
            cast = TVSeriesCast(
                tv_series_id=tv_series.id,
                person_id=person.id,
                character=cast_data.get("character"),
                credit_id=cast_data.get("credit_id"),
                cast_order=cast_data.get("order")
            )
            self.db.add(cast)

        # Crew
        for crew_data in credits_data.get("crew", [])[:100]:
            person = self._get_or_create_person(crew_data)
            crew = TVSeriesCrew(
                tv_series_id=tv_series.id,
                person_id=person.id,
                department=crew_data.get("department"),
                job=crew_data.get("job"),
                credit_id=crew_data.get("credit_id")
            )
            self.db.add(crew)

    def _parse_tv_external_ids(self, tv_series: TVSeries, external_ids: Dict[str, Any]):
        """Parse TV series external IDs."""
        if not external_ids:
            return

        ext_id = self.db.query(ExternalIdTVSeries).filter_by(tv_series_id=tv_series.id).first()
        if not ext_id:
            ext_id = ExternalIdTVSeries(tv_series_id=tv_series.id)
            self.db.add(ext_id)

        ext_id.imdb_id = external_ids.get("imdb_id") or None
        ext_id.tvdb_id = external_ids.get("tvdb_id") or None
        ext_id.tvrage_id = external_ids.get("tvrage_id") or None
        ext_id.wikidata_id = external_ids.get("wikidata_id") or None
        ext_id.facebook_id = external_ids.get("facebook_id") or None
        ext_id.instagram_id = external_ids.get("instagram_id") or None
        ext_id.twitter_id = external_ids.get("twitter_id") or None
        ext_id.freebase_mid = external_ids.get("freebase_mid") or None
        ext_id.freebase_id = external_ids.get("freebase_id") or None

    def _parse_tv_keywords(self, tv_series: TVSeries, keywords_data: Dict[str, Any]):
        """Parse TV series keywords."""
        # Clear existing associations
        self.db.execute(
            text("DELETE FROM tv_series_keywords WHERE tv_series_id = :tv_series_id"),
            {"tv_series_id": tv_series.id}
        )

        for keyword_data in keywords_data.get("results", []):
            keyword = self._get_or_create_keyword(keyword_data)
            self.db.execute(
                text("INSERT INTO tv_series_keywords (tv_series_id, keyword_id) VALUES (:tv_series_id, :keyword_id) ON CONFLICT DO NOTHING"),
                {"tv_series_id": tv_series.id, "keyword_id": keyword.id}
            )

    def _parse_tv_watch_providers(self, tv_series: TVSeries, providers_data: Dict[str, Any]):
        """Parse TV series watch providers."""
        # Clear existing
        self.db.query(TVSeriesWatchProvider).filter_by(tv_series_id=tv_series.id).delete()

        for country, data in providers_data.get("results", {}).items():
            for provider_type in ["flatrate", "buy", "rent", "ads", "free"]:
                for provider_data in data.get(provider_type, []):
                    provider = self._get_or_create_provider(provider_data)
                    watch_provider = TVSeriesWatchProvider(
                        tv_series_id=tv_series.id,
                        provider_id=provider.id,
                        country_code=country,
                        type=provider_type
                    )
                    self.db.add(watch_provider)

    def _parse_tv_translations(self, tv_series: TVSeries, translations_data: Dict[str, Any]):
        """Parse TV series translations."""
        # Clear existing
        self.db.query(TVSeriesTranslation).filter_by(tv_series_id=tv_series.id).delete()

        for trans_data in translations_data.get("translations", []):
            data = trans_data.get("data", {})
            translation = TVSeriesTranslation(
                tv_series_id=tv_series.id,
                iso_639_1=trans_data.get("iso_639_1", ""),
                iso_3166_1=trans_data.get("iso_3166_1", ""),
                name=data.get("name"),
                overview=data.get("overview"),
                homepage=data.get("homepage"),
                tagline=data.get("tagline")
            )
            self.db.add(translation)

    def _parse_similar_tv_series(self, tv_series: TVSeries, similar_data: Dict[str, Any]):
        """Parse similar TV series."""
        # Clear existing
        self.db.query(SimilarTVSeries).filter_by(tv_series_id=tv_series.id).delete()

        for similar in similar_data.get("results", [])[:20]:
            similar_series = SimilarTVSeries(
                tv_series_id=tv_series.id,
                similar_tv_series_id=similar["id"]
            )
            self.db.add(similar_series)
