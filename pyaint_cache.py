"""Pre-computation cache: key, write and validate ``cmap`` caches.

Extracted from ``bot.py`` into a mixin. Cluster into separate modules as
useful. The methods use ``self.settings`` / ``self._canvas`` / ``self._palette``.
"""
from pyaint_log import log

import hashlib
import json
import os
import time

# Default drawing mode used by the cache signatures (mirrors ``Bot.LAYERED``).
LAYERED = "layered"

class CacheMixin:
    def get_cache_filename(self, image_path, flags=0, mode=LAYERED):
        """Generate a unique cache filename based on image and settings"""
        # Canvas must exist to key the cache, so check before touching the file.
        canvas_info = getattr(self, '_canvas', None)
        if canvas_info is None:
            # Canvas not initialized, can't generate cache filename
            return None

        # Read image file to compute hash
        with open(image_path, 'rb') as f:
            image_data = f.read()
        image_hash = hashlib.md5(image_data).hexdigest()[:8]

        settings_str = f"{self.settings}_{flags}_{mode}_{canvas_info}"
        settings_hash = hashlib.md5(settings_str.encode()).hexdigest()[:8]

        # Create cache directory if it doesn't exist
        cache_dir = 'cache'
        os.makedirs(cache_dir, exist_ok=True)

        return f"{cache_dir}/{image_hash}_{settings_hash}.json"

    def precompute(self, image_path, flags=0, mode=LAYERED):
        """Pre-compute the image processing and save to cache"""
        cache_file = self.get_cache_filename(image_path, flags, mode)
        if cache_file is None:
            raise RuntimeError("Cannot precompute: canvas not initialized")

        log.info("Pre-computing image...")

        start_time = time.time()

        # Process the image
        cmap = self.process(image_path, flags, mode)

        # Prepare cache data - convert tuple keys to strings for JSON serialization
        cmap_json = {str(k): v for k, v in cmap.items()}
        cache_data = {
            'cmap': cmap_json,
            'settings': self.settings.copy(),
            'flags': flags,
            'mode': mode,
            'canvas': self._canvas,
            'image_hash': hashlib.md5(open(image_path, 'rb').read()).hexdigest()[:8],
            'timestamp': time.time(),
            'palette_info': {
                'colors_pos': {str(k): v for k, v in dict(self._palette.colors_pos).items()} if hasattr(self, '_palette') and self._palette else None,
                'colors': [list(c) for c in self._palette.colors] if hasattr(self, '_palette') and self._palette else None
            } if hasattr(self, '_palette') else None
        }

        # Save to cache file
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

        actual_time = time.time() - start_time
        log.info(f"Pre-computation completed in {actual_time:.2f} seconds")
        log.info(f"Cache saved to: {cache_file}")

        return cache_file

    def load_cached(self, cache_file):
        """Load and validate cached computation results"""
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)

            # Basic validation
            required_keys = ['cmap', 'settings', 'flags', 'mode', 'canvas', 'timestamp']
            if not all(key in cache_data for key in required_keys):
                return None

            # Check if cache is recent (within 24 hours)
            if time.time() - cache_data['timestamp'] > 24 * 3600:
                return None

            # Validate settings match
            if cache_data['settings'] != self.settings:
                return None

            # Validate canvas matches
            if tuple(cache_data['canvas']) != tuple(self._canvas):
                return None

            # Convert string keys back to tuples for cmap
            cmap_restored = {}
            for k, v in cache_data['cmap'].items():
                # Parse tuple from string like "(255, 0, 0)"
                try:
                    # Remove parentheses and split by comma
                    tuple_str = k.strip('()')
                    tuple_parts = [int(x.strip()) for x in tuple_str.split(',')]
                    tuple_key = tuple(tuple_parts)
                    cmap_restored[tuple_key] = v
                except (ValueError, TypeError):
                    # Skip invalid keys
                    continue

            cache_data['cmap'] = cmap_restored
            return cache_data

        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def get_cached_status(self, image_path, flags=0, mode=LAYERED):
        """Check if valid cached computation exists"""
        cache_file = self.get_cache_filename(image_path, flags, mode)
        if cache_file is None:
            return False, None
        cache_data = self.load_cached(cache_file)
        return cache_data is not None, cache_file
