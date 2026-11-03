from dataclasses import asdict, dataclass
from pathlib import Path
from .paths import bundled_tool, data_root
from .storage import read_json, write_json


@dataclass
class Settings:
    output_dir: str = str(Path.home() / "Documents/字幕工坊")
    ffmpeg: str = ""
    ffprobe: str = ""
    whisper: str = ""
    language: str = "zh"
    model: str = "base"

    def tool(self, name: str) -> Path:
        value = getattr(self, "whisper" if name == "whisper-cli" else name)
        return Path(value).expanduser().resolve() if value else bundled_tool(name)

    @classmethod
    def load(cls) -> "Settings":
        raw = read_json(data_root() / "settings.json", {})
        if not isinstance(raw, dict):
            return cls()
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__ and isinstance(v, str)})

    def save(self) -> None:
        write_json(data_root() / "settings.json", asdict(self))
