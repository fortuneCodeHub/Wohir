#!/usr/bin/python3
"""
Persona Generator System
Generates realistic user personas using Faker
Author: Fortune Nwohiri
"""

import random
import hashlib
from dataclasses import dataclass
from typing import List, Dict, Optional
from faker import Faker
import logging

from .device_profiles import DeviceType

logger = logging.getLogger(__name__)


@dataclass
class UserPersona:
    """Represents a fake user persona for each bot"""
    first_name: str
    last_name: str
    gender: str
    age: int
    email: str
    occupation: str
    interests: List[str]
    location: str
    user_id: str
    search_behavior: Dict
    browsing_patterns: Dict
    
    def __post_init__(self):
        """Generate unique user ID if not provided"""
        if not self.user_id:
            self.user_id = hashlib.md5(
                f"{self.first_name}{self.last_name}{self.email}".encode()
            ).hexdigest()[:12]


class PersonaGenerator:
    """Generates realistic user personas based on device types and demographics"""
    
    def __init__(self):
        self.faker = Faker()
        
        # Interest pools by category
        self.interest_categories = {
            "technology": [
                "Smartphones", "Laptops", "Gaming", "Software", "AI", "Programming",
                "Tech Reviews", "Gadgets", "Mobile Apps", "Web Development"
            ],
            "lifestyle": [
                "Fashion", "Beauty", "Fitness", "Health", "Cooking", "Travel",
                "Photography", "Art", "Music", "Movies", "Books", "Interior Design"
            ],
            "business": [
                "Entrepreneurship", "Marketing", "Finance", "Real Estate", "Investing",
                "Career Development", "Networking", "Leadership", "Sales", "Consulting"
            ],
            "entertainment": [
                "Streaming", "Gaming", "Sports", "Comedy", "Reality TV", "Documentaries",
                "Podcasts", "YouTube", "Social Media", "Celebrities"
            ],
            "education": [
                "Online Learning", "Tutorials", "Courses", "Certifications", "Research",
                "Academic Papers", "Study Tips", "Language Learning", "Skills Development"
            ],
            "finance": [
                "Personal Loans", "Credit Cards", "Banking", "Investments", "Insurance",
                "Budgeting", "Saving", "Cryptocurrency", "Real Estate", "Retirement"
            ]
        }
        
        # Occupation pools by age group and device type
        self.occupation_pools = {
            "young_adult": [  # 18-25
                "Student", "Intern", "Freelancer", "Entry-level Developer", "Content Creator",
                "Social Media Manager", "Barista", "Retail Worker", "Tutor", "Gig Worker"
            ],
            "adult": [  # 26-40
                "Software Developer", "Marketing Manager", "Sales Representative", "Teacher",
                "Nurse", "Accountant", "Designer", "Engineer", "Consultant", "Project Manager",
                "Financial Advisor", "Real Estate Agent", "Marketing Specialist", "HR Manager"
            ],
            "middle_aged": [  # 41-55
                "Senior Developer", "Director", "VP", "Doctor", "Lawyer", "Senior Manager",
                "Business Owner", "Executive", "Senior Consultant", "Department Head",
                "Investment Banker", "Senior Engineer", "Principal", "Partner"
            ],
            "senior": [  # 56+
                "CEO", "President", "Senior Executive", "Retired", "Board Member",
                "Senior Consultant", "Advisor", "Mentor", "Investor", "Author"
            ]
        }
        
        # Search behavior patterns by device type
        self.search_patterns = {
            DeviceType.IPHONE: {
                "search_frequency": "high",  # Mobile users search more frequently
                "session_duration": "short",  # Shorter attention spans
                "browsing_style": "quick_scan",  # Quick scanning behavior
                "ad_interaction": "high",  # More likely to click ads on mobile
                "social_media": "high"  # High social media usage
            },
            DeviceType.ANDROID: {
                "search_frequency": "high",
                "session_duration": "medium",
                "browsing_style": "mixed",
                "ad_interaction": "medium",
                "social_media": "high"
            },
            DeviceType.WINDOWS: {
                "search_frequency": "medium",
                "session_duration": "long",
                "browsing_style": "detailed",
                "ad_interaction": "low",
                "social_media": "medium"
            },
            DeviceType.MACOS: {
                "search_frequency": "medium",
                "session_duration": "long",
                "browsing_style": "detailed",
                "ad_interaction": "low",
                "social_media": "medium"
            }
        }
        
        # Browsing patterns by persona type
        self.browsing_patterns = {
            "quick_scanner": {
                "scroll_speed": "fast",
                "page_views": "many",
                "time_per_page": "short",
                "click_behavior": "selective"
            },
            "detailed_reader": {
                "scroll_speed": "slow",
                "page_views": "few",
                "time_per_page": "long",
                "click_behavior": "thorough"
            },
            "comparison_shopper": {
                "scroll_speed": "medium",
                "page_views": "many",
                "time_per_page": "medium",
                "click_behavior": "comparative"
            },
            "casual_browser": {
                "scroll_speed": "variable",
                "page_views": "medium",
                "time_per_page": "variable",
                "click_behavior": "random"
            }
        }
    
    def generate_persona(self, device_type: DeviceType, age_override: Optional[int] = None) -> UserPersona:
        """
        Generate a realistic persona based on device type
        
        Args:
            device_type: Type of device the persona will use
            age_override: Specific age to use (if None, generated based on device type)
            
        Returns:
            Complete UserPersona object
        """
        # Generate age based on device type if not overridden
        if age_override is None:
            age = self._generate_age_for_device(device_type)
        else:
            age = age_override
        
        # Generate gender
        gender = random.choice(['male', 'female'])
        
        # Generate name based on gender
        if gender == 'male':
            first_name = self.faker.first_name_male()
        else:
            first_name = self.faker.first_name_female()
        
        last_name = self.faker.last_name()
        
        # Generate email
        email = self.faker.email()
        
        # Generate occupation based on age
        occupation = self._generate_occupation(age)
        
        # Generate interests based on age, gender, and device type
        interests = self._generate_interests(age, gender, device_type)
        
        # Generate location
        location = self.faker.city() + ", " + self.faker.country()
        
        # Generate search behavior based on device type
        search_behavior = self._generate_search_behavior(device_type, age)
        
        # Generate browsing patterns
        browsing_patterns = self._generate_browsing_patterns(device_type, age)
        
        return UserPersona(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            age=age,
            email=email,
            occupation=occupation,
            interests=interests,
            location=location,
            user_id="",  # Will be generated in __post_init__
            search_behavior=search_behavior,
            browsing_patterns=browsing_patterns
        )
    
    def _generate_age_for_device(self, device_type: DeviceType) -> int:
        """Generate age based on device type demographics"""
        if device_type == DeviceType.IPHONE:
            # iPhone users tend to be younger to middle-aged
            return random.choices(
                [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45],
                weights=[2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 1, 1]
            )[0]
        elif device_type == DeviceType.ANDROID:
            # Android users have broader age range
            return random.choices(
                [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60],
                weights=[1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            )[0]
        elif device_type == DeviceType.MACOS:
            # Mac users tend to be professionals
            return random.choices(
                [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50],
                weights=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            )[0]
        else:  # Windows
            # Windows users have the widest range
            return random.randint(18, 65)
    
    def _generate_occupation(self, age: int) -> str:
        """Generate occupation based on age"""
        if age <= 25:
            age_group = "young_adult"
        elif age <= 40:
            age_group = "adult"
        elif age <= 55:
            age_group = "middle_aged"
        else:
            age_group = "senior"
        
        return random.choice(self.occupation_pools[age_group])
    
    def _generate_interests(self, age: int, gender: str, device_type: DeviceType) -> List[str]:
        """Generate interests based on age, gender, and device type"""
        interests = []
        
        # Base interests by age
        if age <= 25:
            # Young adults are more tech-savvy and social
            interests.extend(random.sample(self.interest_categories["technology"], 3))
            interests.extend(random.sample(self.interest_categories["entertainment"], 2))
            interests.extend(random.sample(self.interest_categories["lifestyle"], 2))
        elif age <= 40:
            # Adults focus on career and family
            interests.extend(random.sample(self.interest_categories["business"], 2))
            interests.extend(random.sample(self.interest_categories["finance"], 2))
            interests.extend(random.sample(self.interest_categories["technology"], 2))
            interests.extend(random.sample(self.interest_categories["lifestyle"], 2))
        elif age <= 55:
            # Middle-aged focus on career and investments
            interests.extend(random.sample(self.interest_categories["business"], 3))
            interests.extend(random.sample(self.interest_categories["finance"], 3))
            interests.extend(random.sample(self.interest_categories["education"], 2))
        else:
            # Seniors focus on health and leisure
            interests.extend(random.sample(self.interest_categories["lifestyle"], 3))
            interests.extend(random.sample(self.interest_categories["entertainment"], 2))
            interests.extend(random.sample(self.interest_categories["education"], 2))
        
        # Device-specific interests
        if device_type in [DeviceType.IPHONE, DeviceType.ANDROID]:
            # Mobile users more interested in apps and social media
            if "Social Media" not in interests:
                interests.append("Social Media")
            if "Mobile Apps" not in interests:
                interests.append("Mobile Apps")
        elif device_type == DeviceType.MACOS:
            # Mac users more interested in design and creativity
            if "Design" not in interests:
                interests.append("Design")
            if "Photography" not in interests:
                interests.append("Photography")
        
        # Gender-specific interests (subtle differences)
        if gender == 'female' and random.random() < 0.3:
            interests.extend(["Beauty", "Fashion"])
        elif gender == 'male' and random.random() < 0.3:
            interests.extend(["Sports", "Gaming"])
        
        # Ensure we have 4-8 interests
        return random.sample(interests, min(len(interests), random.randint(4, 8)))
    
    def _generate_search_behavior(self, device_type: DeviceType, age: int) -> Dict:
        """Generate search behavior patterns based on device type and age"""
        base_pattern = self.search_patterns[device_type].copy()
        
        # Age-based modifications
        if age <= 25:
            base_pattern["search_frequency"] = "high"
            base_pattern["session_duration"] = "short"
        elif age >= 50:
            base_pattern["search_frequency"] = "low"
            base_pattern["session_duration"] = "long"
        
        # Add specific search patterns
        search_behavior = {
            **base_pattern,
            "keyword_length": random.choice(["short", "medium", "long"]),
            "search_refinement": random.choice(["frequent", "occasional", "rare"]),
            "voice_search": random.choice([True, False]) if device_type in [DeviceType.IPHONE, DeviceType.ANDROID] else False,
            "image_search": random.choice([True, False]),
            "shopping_behavior": random.choice(["browser", "buyer", "researcher"]),
            "news_consumption": random.choice(["high", "medium", "low"]),
            "social_media_usage": random.choice(["high", "medium", "low"])
        }
        
        return search_behavior
    
    def _generate_browsing_patterns(self, device_type: DeviceType, age: int) -> Dict:
        """Generate browsing patterns based on device type and age"""
        # Select base pattern
        if age <= 25:
            pattern_type = random.choice(["quick_scanner", "casual_browser"])
        elif age <= 40:
            pattern_type = random.choice(["comparison_shopper", "detailed_reader"])
        else:
            pattern_type = random.choice(["detailed_reader", "casual_browser"])
        
        base_pattern = self.browsing_patterns[pattern_type].copy()
        
        # Device-specific modifications
        if device_type in [DeviceType.IPHONE, DeviceType.ANDROID]:
            base_pattern["scroll_speed"] = "fast"
            base_pattern["time_per_page"] = "short"
        else:
            base_pattern["scroll_speed"] = "slow"
            base_pattern["time_per_page"] = "long"
        
        # Add additional patterns
        browsing_patterns = {
            **base_pattern,
            "tab_usage": random.choice(["few", "many"]),
            "bookmark_behavior": random.choice(["frequent", "occasional", "rare"]),
            "popup_interaction": random.choice(["close_immediately", "read_then_close", "interact"]),
            "ad_blocking": random.choice([True, False]),
            "incognito_usage": random.choice(["frequent", "occasional", "rare"]),
            "form_completion": random.choice(["quick", "careful", "abandoned"]),
            "video_watching": random.choice(["high", "medium", "low"]),
            "reading_behavior": random.choice(["skim", "thorough", "selective"])
        }
        
        return browsing_patterns
    
    def generate_search_keywords(self, persona: UserPersona, base_keywords: List[str] = None) -> List[str]:
        """
        Generate search keywords based on persona interests and behavior
        
        Args:
            persona: UserPersona object
            base_keywords: Base keywords to work with (optional)
            
        Returns:
            List of generated search keywords
        """
        if base_keywords is None:
            base_keywords = ["best", "top", "review", "buy", "how to", "guide", "compare", "price"]
        
        keywords = []
        
        # Generate keywords based on interests
        for interest in persona.interests[:3]:  # Use top 3 interests
            for base in base_keywords[:3]:  # Use top 3 base keywords
                keyword = f"{base} {interest.lower()}"
                keywords.append(keyword)
        
        # Add some random variations
        variations = [
            f"{interest} 2024" for interest in persona.interests[:2]
        ]
        keywords.extend(variations)
        
        # Add persona-specific keywords
        if persona.search_behavior.get("shopping_behavior") == "buyer":
            keywords.extend([f"buy {interest}" for interest in persona.interests[:2]])
        elif persona.search_behavior.get("shopping_behavior") == "researcher":
            keywords.extend([f"compare {interest}" for interest in persona.interests[:2]])
        
        # Shuffle and return unique keywords
        return list(set(keywords))[:10]  # Return max 10 keywords
    
    def get_persona_summary(self, persona: UserPersona) -> str:
        """
        Get a summary of the persona for logging
        
        Args:
            persona: UserPersona object
            
        Returns:
            Formatted summary string
        """
        summary = f"\nPersona: {persona.first_name} {persona.last_name}\n"
        summary += f"Age: {persona.age}, Gender: {persona.gender}\n"
        summary += f"Occupation: {persona.occupation}\n"
        summary += f"Location: {persona.location}\n"
        summary += f"Interests: {', '.join(persona.interests[:5])}\n"
        summary += f"Search Behavior: {persona.search_behavior['search_frequency']} frequency, {persona.search_behavior['session_duration']} sessions\n"
        summary += f"Browsing Style: {persona.browsing_patterns['scroll_speed']} scrolling, {persona.browsing_patterns['time_per_page']} page time\n"
        
        return summary
