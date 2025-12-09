import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_dir = project_root / "src"

sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(project_root))
