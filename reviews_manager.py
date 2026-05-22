"""
Reviews Manager Module
Handles storage, retrieval, and merging of structured student reviews
organized by subject code and category.

FOLDER STRUCTURE (separated from MCQ/PDF paths):
─────────────────────────────────────────────────
  Reviews are stored in DEDICATED folders under Documents:
    - Mids reviews:   ~/Documents/vu-reviews-mids/{subject_code}/reviews_mids.json
    - Finals reviews: ~/Documents/vu-reviews-finals/{subject_code}/reviews_finals.json
    - Custom reviews: ~/Documents/vu-reviews-custom/{subject_code}/reviews_{category}.json

  This is SEPARATE from:
    - MCQ/Short Notes JSON: ~/Documents/vu-all-JSON/  (json_output_root)
    - Generated PDFs:       ~/Documents/vu-generated-PDFs/

  IMPORTANT FOR FUTURE AI AGENTS:
    - NEVER mix review paths with MCQ/PDF paths
    - Each data type has its OWN dedicated root folder
    - The old reviews.json (without prefix) is legacy = mids data
    - Always use get_reviews_root(category) to get the correct base path

Each reviews_{category}.json contains a list of review objects with:
  - subject_code: str
  - category: str
  - review: str (English translated)
  - review_date: str or null
  - id: int (auto-assigned)
"""

import json
import shutil
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from folder_organizer import get_json_output_root

# Global lock for thread-safe file operations
# RLock (Reentrant Lock) is required because add_reviews() holds the lock
# and then calls save_reviews(), which also needs to acquire the same lock.
# A regular Lock() would deadlock here since it is NOT reentrant.
_reviews_lock = threading.RLock()


def _sanitize_category(category: str) -> str:
    """
    Sanitize a category name for use in filenames.
    Converts to lowercase and replaces spaces with underscores.

    Args:
        category: Raw category name

    Returns:
        Sanitized category string safe for filenames
    """
    return category.strip().lower().replace(' ', '_')


class ReviewsManager:
    """Manages structured reviews storage per subject code and category"""

    def __init__(self):
        self.output_root = Path(get_json_output_root())
        self.output_root.mkdir(parents=True, exist_ok=True)

    def _get_reviews_file(self, subject_code: str, category: str = 'uncategorized') -> Path:
        """
        Get the reviews JSON path for a subject code and category.

        MIGRATION LOGIC (backward compatibility):
        - Old format: reviews.json (plain, no category prefix) = this is MIDS data
        - New format: reviews_mids.json, reviews_finals.json, reviews_{category}.json
        
        When category='mids' is requested and reviews_mids.json doesn't exist,
        but the old reviews.json does exist, it gets auto-migrated to reviews_mids.json.

        Args:
            subject_code: Subject code (e.g., 'MGT501', 'CS101')
            category: Review category (default: 'uncategorized')

        Returns:
            Path to the category-specific reviews file
        """
        sanitized = _sanitize_category(category)
        subject_dir = self.output_root / subject_code
        subject_dir.mkdir(parents=True, exist_ok=True)

        new_file = subject_dir / f"reviews_{sanitized}.json"

        # Auto-migration: old reviews.json → reviews_mids.json
        # The old reviews.json was ALWAYS mids data (before the mids/finals split).
        # This migration triggers when:
        #   1. We're looking for 'mids' category
        #   2. reviews_mids.json doesn't exist yet
        #   3. But the old reviews.json does exist
        if sanitized == 'mids' and not new_file.exists():
            old_file = subject_dir / "reviews.json"
            if old_file.exists():
                try:
                    shutil.copy2(str(old_file), str(new_file))
                    old_file.unlink()
                    print(f"✓ Migrated {old_file.name} → {new_file.name} for {subject_code}")
                except Exception as e:
                    print(f"⚠️ Migration failed for {subject_code}: {e}")

        return new_file

    def load_reviews(self, subject_code: str, category: str = 'uncategorized') -> List[Dict[str, Any]]:
        """
        Load existing reviews for a subject code and category.

        Args:
            subject_code: Subject code (e.g., 'MGT501', 'CS101')
            category: Review category (default: 'uncategorized')

        Returns:
            List of review dictionaries
        """
        file_path = self._get_reviews_file(subject_code, category)
        if not file_path.exists():
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reviews = json.load(f)
            return reviews if isinstance(reviews, list) else []
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ Failed to load reviews for {subject_code}/{category}: {e}")
            return []

    def save_reviews(self, subject_code: str, reviews: List[Dict[str, Any]], category: str = 'uncategorized') -> str:
        """
        Save reviews for a subject code and category (overwrites existing).

        Args:
            subject_code: Subject code
            reviews: List of review dictionaries
            category: Review category (default: 'uncategorized')

        Returns:
            Path to saved file
        """
        file_path = self._get_reviews_file(subject_code, category)

        with _reviews_lock:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(reviews, f, indent=2, ensure_ascii=False)
                # Note: intentionally no print() here — callers handle logging
                return str(file_path)
            except Exception as e:
                raise Exception(f"Failed to save reviews for {subject_code}/{category}: {e}")

    def add_reviews(self, new_reviews: List[Dict[str, Any]], category: str = 'uncategorized') -> Dict[str, int]:
        """
        Add new reviews, merging with existing ones per subject code.
        Deduplicates by review text (exact match).

        Args:
            new_reviews: List of review dicts with subject_code, review, review_date
            category: Review category to store under (default: 'uncategorized')

        Returns:
            Dictionary of {subject_code: count_added}
        """
        sanitized = _sanitize_category(category)

        # Group by subject code
        grouped = {}
        for review in new_reviews:
            code = review.get('subject_code', 'UNKNOWN').upper().strip()
            if code not in grouped:
                grouped[code] = []
            grouped[code].append(review)

        results = {}

        for subject_code, reviews in grouped.items():
            with _reviews_lock:
                # Load existing
                existing = self.load_reviews(subject_code, sanitized)
                existing_texts = {r.get('review', '').strip().lower() for r in existing}

                # Find max existing ID
                max_id = 0
                for r in existing:
                    rid = r.get('id', 0)
                    if isinstance(rid, int) and rid > max_id:
                        max_id = rid

                # Deduplicate and add
                added = 0
                for review in reviews:
                    review_text = review.get('review', '').strip()
                    if review_text.lower() not in existing_texts:
                        max_id += 1
                        clean_review = {
                            'id': max_id,
                            'subject_code': subject_code,
                            'category': sanitized,
                            'review': review_text,
                            'review_date': review.get('review_date', None)
                        }
                        existing.append(clean_review)
                        existing_texts.add(review_text.lower())
                        added += 1

                # Save merged
                if added > 0:
                    self.save_reviews(subject_code, existing, sanitized)

                results[subject_code] = added

        return results

    def get_review_count(self, subject_code: str, category: Optional[str] = None) -> int:
        """
        Get count of reviews for a subject code.

        Args:
            subject_code: Subject code
            category: If provided, count only that category.
                      If None, count ALL reviews across all categories.

        Returns:
            Number of reviews
        """
        if category is not None:
            reviews = self.load_reviews(subject_code, category)
            return len(reviews)

        # Count across all categories
        subject_dir = self.output_root / subject_code
        if not subject_dir.exists() or not subject_dir.is_dir():
            return 0

        total = 0
        for reviews_file in subject_dir.glob("reviews_*.json"):
            try:
                with open(reviews_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    total += len(data)
            except (json.JSONDecodeError, Exception):
                continue
        return total

    def migrate_all_legacy_reviews(self):
        """
        Bulk migration: scan ALL subject folders for old reviews.json files
        and rename them to reviews_mids.json.
        
        This should be called once on startup to ensure all legacy data is accessible.
        The old reviews.json (without category prefix) was ALWAYS mids data.
        """
        if not self.output_root.exists():
            return
        
        migrated_count = 0
        for subject_dir in self.output_root.iterdir():
            if not subject_dir.is_dir():
                continue
            
            old_file = subject_dir / "reviews.json"
            new_file = subject_dir / "reviews_mids.json"
            
            if old_file.exists() and not new_file.exists():
                try:
                    shutil.copy2(str(old_file), str(new_file))
                    old_file.unlink()
                    migrated_count += 1
                except Exception as e:
                    print(f"⚠️ Migration failed for {subject_dir.name}: {e}")
        
        if migrated_count > 0:
            print(f"✓ Bulk migration complete: {migrated_count} reviews.json → reviews_mids.json")

    def get_all_review_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get review statistics for all subjects that have reviews,
        grouped by subject code and category.

        Returns:
            Dictionary of:
            {
                subject_code: {
                    'categories': {
                        category: {
                            'count': int,
                            'last_date': str or None
                        }
                    },
                    'total_count': int
                }
            }
        """
        stats = {}

        if not self.output_root.exists():
            return stats

        for subject_dir in sorted(self.output_root.iterdir()):
            if not subject_dir.is_dir():
                continue

            categories = {}
            total_count = 0

            for reviews_file in sorted(subject_dir.glob("reviews_*.json")):
                try:
                    with open(reviews_file, 'r', encoding='utf-8') as f:
                        reviews = json.load(f)

                    if not isinstance(reviews, list) or len(reviews) == 0:
                        continue

                    # Extract category name from filename: reviews_{category}.json
                    cat_name = reviews_file.stem.replace('reviews_', '', 1)

                    # Find the latest date
                    dates = [r.get('review_date') for r in reviews if r.get('review_date')]
                    last_date = max(dates) if dates else None

                    categories[cat_name] = {
                        'count': len(reviews),
                        'last_date': last_date
                    }
                    total_count += len(reviews)
                except (json.JSONDecodeError, Exception):
                    continue

            if categories:
                stats[subject_dir.name] = {
                    'categories': categories,
                    'total_count': total_count
                }

        return stats

    def get_all_categories(self) -> List[str]:
        """
        Scan all subjects and return unique category names.

        Returns:
            Sorted list of unique category names found across all subjects
        """
        categories: Set[str] = set()

        if not self.output_root.exists():
            return []

        for subject_dir in self.output_root.iterdir():
            if not subject_dir.is_dir():
                continue

            for reviews_file in subject_dir.glob("reviews_*.json"):
                # Extract category name from filename: reviews_{category}.json
                cat_name = reviews_file.stem.replace('reviews_', '', 1)
                categories.add(cat_name)

        return sorted(categories)

    def get_reviews_for_prompt(self, subject_code: str, category: str = 'uncategorized', max_reviews: int = 20) -> str:
        """
        Get reviews formatted as context for MCQ/short notes generation prompts.

        The header format MUST match what server.js prompts instruct the model to look for:
        "--- PAST PAPER REVIEWS ---"

        Args:
            subject_code: Subject code to get reviews for
            category: Review category (default: 'uncategorized')
            max_reviews: Maximum number of reviews to include

        Returns:
            Formatted string of reviews for prompt context, or empty string
        """
        reviews = self.load_reviews(subject_code, category)
        if not reviews:
            return ""

        sanitized = _sanitize_category(category)

        # Take most recent reviews (by ID, higher = newer)
        reviews = sorted(reviews, key=lambda r: r.get('id', 0), reverse=True)[:max_reviews]

        # NOTE: The header "--- PAST PAPER REVIEWS ---" MUST match exactly what
        # server.js system prompts instruct Gemini to look for. Do NOT change this header.
        lines = ["\n\n--- PAST PAPER REVIEWS ---"]
        lines.append(f"These are REAL topics from actual VU past papers ({sanitized.upper()} exams), submitted by students.")
        lines.append("Read each topic carefully. Topics that appear frequently have the HIGHEST exam probability.")
        lines.append("For each topic that matches the current batch content, generate 2 EXTRA items covering that concept.")
        lines.append("")
        lines.append("Review Topics:")
        for r in reviews:
            lines.append(f"- {r.get('review', '')}")
        lines.append("--- END PAST PAPER REVIEWS ---\n")

        return "\n".join(lines)

    def get_raw_review_topics(self, subject_code: str, category: str = 'uncategorized', max_reviews: int = 20) -> list:
        """
        Get raw review topic strings for embedding directly in the system prompt.

        Unlike get_reviews_for_prompt() which returns a formatted text block to
        append at the end of the user text, this returns a plain list of topic
        strings. The server.js system prompt builder uses these to embed reviews
        directly into the system prompt — making them impossible for the model
        to ignore.

        Args:
            subject_code: Subject code to get reviews for (e.g., 'ENG')
            category: Review category ('mids', 'finals', etc.)
            max_reviews: Maximum number of reviews to include

        Returns:
            List of review topic strings, or empty list
        """
        reviews = self.load_reviews(subject_code, category)
        if not reviews:
            return []

        # Take most recent reviews (by ID, higher = newer)
        reviews = sorted(reviews, key=lambda r: r.get('id', 0), reverse=True)[:max_reviews]

        return [r.get('review', '').strip() for r in reviews if r.get('review', '').strip()]

    def delete_reviews(self, subject_code: str, category: Optional[str] = None) -> bool:
        """
        Delete reviews for a subject code.

        Args:
            subject_code: Subject code
            category: If provided, delete only that category's reviews.
                      If None, delete ALL category files for that subject.

        Returns:
            True if any files were deleted
        """
        if category is not None:
            file_path = self._get_reviews_file(subject_code, category)
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"✓ Deleted reviews for {subject_code}/{category}")
                    return True
                except Exception as e:
                    print(f"⚠️ Failed to delete reviews for {subject_code}/{category}: {e}")
                    return False
            return False

        # Delete all category files for this subject
        subject_dir = self.output_root / subject_code
        if not subject_dir.exists() or not subject_dir.is_dir():
            return False

        deleted_any = False
        for reviews_file in subject_dir.glob("reviews_*.json"):
            try:
                reviews_file.unlink()
                deleted_any = True
            except Exception as e:
                print(f"⚠️ Failed to delete {reviews_file.name} for {subject_code}: {e}")

        if deleted_any:
            print(f"✓ Deleted all review categories for {subject_code}")
        return deleted_any


# Global instance — runs bulk migration on first import
_manager = ReviewsManager()
_manager.migrate_all_legacy_reviews()


def add_reviews(new_reviews: List[Dict[str, Any]], category: str = 'uncategorized') -> Dict[str, int]:
    """Convenience function to add reviews"""
    return _manager.add_reviews(new_reviews, category)


def get_all_review_stats() -> Dict[str, Dict[str, Any]]:
    """Convenience function to get all review stats"""
    return _manager.get_all_review_stats()


def get_review_count(subject_code: str, category: Optional[str] = None) -> int:
    """Convenience function to get review count for a subject"""
    return _manager.get_review_count(subject_code, category)


def get_reviews_for_prompt(subject_code: str, category: str = 'uncategorized', max_reviews: int = 20) -> str:
    """Convenience function to get reviews formatted for prompts"""
    return _manager.get_reviews_for_prompt(subject_code, category, max_reviews)


def load_reviews(subject_code: str, category: str = 'uncategorized') -> List[Dict[str, Any]]:
    """Convenience function to load reviews"""
    return _manager.load_reviews(subject_code, category)


def get_all_categories() -> List[str]:
    """Convenience function to get all unique category names"""
    return _manager.get_all_categories()


def get_raw_review_topics(subject_code: str, category: str = 'uncategorized', max_reviews: int = 20) -> list:
    """Convenience function to get raw review topic strings for system prompt embedding"""
    return _manager.get_raw_review_topics(subject_code, category, max_reviews)
