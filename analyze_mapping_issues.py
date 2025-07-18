#!/usr/bin/env python3
"""
Script to analyze postal code to weather area mapping issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select
from app.core.database import get_sync_session
from app.models.postal_code import PostalCode
from app.models.weather_area import WeatherArea
from app.services.postal_code_weather_mapping_service import PostalCodeWeatherMappingService
from collections import Counter, defaultdict
import re

def analyze_mapping_issues():
    """Analyze why postal codes fail to map to weather areas"""
    
    session = get_sync_session()
    
    # Get all unmapped postal codes
    unmapped_postal_codes = session.exec(
        select(PostalCode).where(PostalCode.weather_area_id.is_(None))
    ).all()
    
    print(f"Total unmapped postal codes: {len(unmapped_postal_codes)}")
    
    # Get all weather areas
    weather_areas = session.exec(select(WeatherArea)).all()
    weather_areas_dict = {}
    for wa in weather_areas:
        key = f"{wa.prefecture}_{wa.city}"
        weather_areas_dict[key] = wa
    
    print(f"Total weather areas: {len(weather_areas)}")
    
    # Analyze prefecture matches
    prefecture_issues = Counter()
    city_format_issues = defaultdict(list)
    partial_matches = []
    
    # Sample some unmapped postal codes for analysis
    sample_size = min(100, len(unmapped_postal_codes))
    sample_unmapped = unmapped_postal_codes[:sample_size]
    
    print(f"\nAnalyzing sample of {sample_size} unmapped postal codes:")
    
    for postal_code in sample_unmapped:
        prefecture = postal_code.prefecture
        city = postal_code.city
        
        # Check if prefecture exists in weather areas
        prefecture_weather_areas = [wa for wa in weather_areas if wa.prefecture == prefecture]
        
        if not prefecture_weather_areas:
            prefecture_issues[prefecture] += 1
            continue
            
        # Check city name variations
        found_exact_match = False
        found_partial_match = False
        
        # Exact match
        exact_key = f"{prefecture}_{city}"
        if exact_key in weather_areas_dict:
            found_exact_match = True
        
        # Partial matches
        for wa in prefecture_weather_areas:
            if city in wa.city or wa.city in city:
                found_partial_match = True
                partial_matches.append({
                    'postal_code': postal_code.postal_code,
                    'postal_prefecture': prefecture,
                    'postal_city': city,
                    'weather_prefecture': wa.prefecture,
                    'weather_city': wa.city,
                    'weather_region': wa.region
                })
                break
        
        if not found_exact_match and not found_partial_match:
            city_format_issues[prefecture].append({
                'postal_code': postal_code.postal_code,
                'city': city,
                'available_cities': [wa.city for wa in prefecture_weather_areas]
            })
    
    # Print analysis results
    print("\n=== ANALYSIS RESULTS ===")
    
    print(f"\n1. Prefecture Issues ({len(prefecture_issues)} prefectures):")
    for prefecture, count in prefecture_issues.most_common():
        print(f"   - {prefecture}: {count} postal codes")
    
    print(f"\n2. City Format Issues ({len(city_format_issues)} prefectures):")
    for prefecture, issues in city_format_issues.items():
        print(f"   - {prefecture}: {len(issues)} unmapped cities")
        for issue in issues[:5]:  # Show first 5 examples
            print(f"     * Postal: {issue['city']}")
            print(f"       Available: {issue['available_cities'][:10]}")  # Show first 10
    
    print(f"\n3. Partial Matches Found ({len(partial_matches)} cases):")
    for match in partial_matches[:10]:  # Show first 10
        print(f"   - Postal: {match['postal_prefecture']} {match['postal_city']}")
        print(f"     Weather: {match['weather_prefecture']} {match['weather_city']} ({match['weather_region']})")
    
    # Analyze common patterns
    print("\n4. Common City Name Pattern Issues:")
    
    # Check for specific patterns
    patterns = {
        "City districts": r"市.+区",
        "Prefecture cities": r"県.+市",
        "Towns": r"町$",
        "Villages": r"村$",
        "Special wards": r"特別区"
    }
    
    pattern_counts = {pattern: 0 for pattern in patterns}
    
    for postal_code in sample_unmapped:
        city = postal_code.city
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, city):
                pattern_counts[pattern_name] += 1
    
    for pattern, count in pattern_counts.items():
        print(f"   - {pattern}: {count} postal codes")
    
    # Check for exact weather area city formats
    print("\n5. Weather Area City Format Examples:")
    weather_city_examples = list(set(wa.city for wa in weather_areas))[:20]
    for city in weather_city_examples:
        print(f"   - {city}")
    
    print("\n6. Postal Code City Format Examples:")
    postal_city_examples = list(set(pc.city for pc in sample_unmapped))[:20]
    for city in postal_city_examples:
        print(f"   - {city}")
    
    # Test mapping service logic
    print("\n7. Testing Mapping Service Logic:")
    mapping_service = PostalCodeWeatherMappingService(session)
    
    test_cases = sample_unmapped[:5]
    for postal_code in test_cases:
        weather_area = mapping_service._find_weather_area_for_postal_code(postal_code)
        print(f"   - {postal_code.prefecture} {postal_code.city} -> {weather_area.city if weather_area else 'None'}")

if __name__ == "__main__":
    analyze_mapping_issues()