from pathlib import Path
from stat import S_IXUSR

process_matsim_events = Path(__file__).parent / "process_matsim_events.sh"
process_matsim_events.chmod(0o100777)
