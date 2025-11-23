#!/bin/bash

# TMDB Database Query Helper Script
# Usage: ./query_db.sh

echo "TMDB Database Query Helper"
echo "=========================="
echo ""

# Function to run a query
run_query() {
    docker exec tmdb_postgres psql -U postgres -d tmdb -c "$1"
}

# Main menu
while true; do
    echo ""
    echo "Select a query to run:"
    echo "1.  Overall Statistics"
    echo "2.  Processing Status"
    echo "3.  Recent Movies (top 10)"
    echo "4.  Top Rated Movies"
    echo "5.  Genre Distribution"
    echo "6.  Recent TV Series (top 10)"
    echo "7.  Most Prolific Actors"
    echo "8.  Failed Items"
    echo "9.  Database Tables List"
    echo "10. Custom Query"
    echo "11. Dashboard Stats (JSON)"
    echo "0.  Exit"
    echo ""
    read -p "Enter your choice: " choice

    case $choice in
        1)
            echo "Overall Statistics:"
            run_query "SELECT 
                (SELECT COUNT(*) FROM movies) as total_movies,
                (SELECT COUNT(*) FROM tv_series) as total_tv_series,
                (SELECT COUNT(*) FROM people) as total_people,
                (SELECT COUNT(*) FROM genres) as total_genres,
                (SELECT COUNT(*) FROM keywords) as total_keywords;"
            ;;
        2)
            echo "Processing Status:"
            run_query "SELECT content_type, status, COUNT(*) as count 
                FROM processing_state 
                GROUP BY content_type, status 
                ORDER BY content_type, status;"
            ;;
        3)
            echo "Recent Movies:"
            run_query "SELECT id, title, release_date, vote_average, vote_count, popularity 
                FROM movies 
                ORDER BY updated_at DESC 
                LIMIT 10;"
            ;;
        4)
            echo "Top Rated Movies (min 100 votes):"
            run_query "SELECT id, title, release_date, vote_average, vote_count, popularity 
                FROM movies 
                WHERE vote_count >= 100 
                ORDER BY vote_average DESC, vote_count DESC 
                LIMIT 10;"
            ;;
        5)
            echo "Genre Distribution:"
            run_query "SELECT g.name, COUNT(mg.movie_id) as movie_count 
                FROM genres g 
                LEFT JOIN movie_genres mg ON g.id = mg.genre_id 
                GROUP BY g.id, g.name 
                ORDER BY movie_count DESC 
                LIMIT 20;"
            ;;
        6)
            echo "Recent TV Series:"
            run_query "SELECT id, name, first_air_date, vote_average, vote_count, popularity 
                FROM tv_series 
                ORDER BY updated_at DESC 
                LIMIT 10;"
            ;;
        7)
            echo "Most Prolific Actors:"
            run_query "SELECT p.name, COUNT(mc.movie_id) as movie_count, p.popularity 
                FROM people p 
                INNER JOIN movie_cast mc ON p.id = mc.person_id 
                GROUP BY p.id, p.name, p.popularity 
                ORDER BY movie_count DESC 
                LIMIT 20;"
            ;;
        8)
            echo "Failed Items:"
            run_query "SELECT content_type, tmdb_id, error_message, retry_count, last_attempt 
                FROM processing_state 
                WHERE status = 'failed' 
                ORDER BY last_attempt DESC 
                LIMIT 10;"
            ;;
        9)
            echo "Database Tables:"
            run_query "\dt"
            ;;
        10)
            read -p "Enter your SQL query: " custom_query
            run_query "$custom_query"
            ;;
        11)
            echo "Dashboard Stats (accessing API):"
            curl -s http://localhost:8080/api/stats | python3 -m json.tool
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            ;;
    esac
done
