"""Local custom EQ memories. Loading never sends a speaker command."""
import json
from pathlib import Path


def validate_profile(name, bands):
    name = name.strip()
    if not name or len(name) > 32:
        raise ValueError('Give your EQ a name of 1–32 characters.')
    if not isinstance(bands, (list, tuple)) or len(bands) != 5 or any(
            isinstance(value, bool) or not isinstance(value, int) or not -128 <= value <= 127
            for value in bands):
        raise ValueError('An EQ memory needs five whole-number band levels from −128 to 127.')
    return name, tuple(bands)


class EQProfiles:
    def __init__(self, path):
        self.path = Path(path)

    def records(self, strict=False):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            if strict: raise ValueError('EQ memory file could not be read. Preserve it and recover from a backup before saving.')
            return {}
        if not isinstance(data, dict):
            if strict: raise ValueError('EQ memory file is invalid. It was not overwritten.')
            return {}
        valid = {}
        for name, bands in list(data.items())[:20]:
            try:
                mode = bands.get('mode') if isinstance(bands, dict) else 4
                bands = bands.get('bands') if isinstance(bands, dict) else bands
                from .settings import EQ_PRESETS
                if isinstance(mode, bool) or not isinstance(mode, int) or mode not in EQ_PRESETS:
                    continue
                name, bands = validate_profile(name, bands)
            except (ValueError, AttributeError):
                continue
            valid[name] = {'mode': mode, 'bands': bands}
        return valid

    def load(self):
        return {name: record['bands'] for name, record in self.records().items()}

    def save(self, name, bands, mode=4):
        name, bands = validate_profile(name, bands)
        from .settings import EQ_PRESETS
        if isinstance(mode, bool) or not isinstance(mode, int) or mode not in EQ_PRESETS:
            raise ValueError('Unknown EQ preset mode.')
        profiles = self.records(strict=True)
        if name not in profiles and len(profiles) >= 20:
            raise ValueError('You have 20 EQ memories. Replace or delete one first.')
        profiles[name] = {'mode': mode, 'bands': bands}
        self._write(profiles)

    def delete(self, name):
        profiles = self.records(strict=True)
        if name not in profiles:
            raise ValueError('Choose a saved EQ memory first.')
        del profiles[name]
        self._write(profiles)

    def _write(self, profiles):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(profiles, indent=2), encoding='utf-8')
        temporary.replace(self.path)
