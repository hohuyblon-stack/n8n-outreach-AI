"""
Job Manager - Manage and persist scheduled job states
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from loguru import logger


@dataclass
class JobRun:
    """Record of a job execution"""
    job_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    result: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "job_name": self.job_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "result": self.result,
            "error": self.error
        }


class JobManager:
    """
    Manages job history and persistence

    Features:
    - Persist job run history to file
    - Track success/failure rates
    - Resume state after restart
    """

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.data_dir / "job_history.json"
        self.state_file = self.data_dir / "scheduler_state.json"

        self.history: List[JobRun] = []
        self.job_states: Dict[str, Dict] = {}

        self._load_state()

    def _load_state(self):
        """Load persisted state"""
        # Load job history
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    # Keep only last 1000 records
                    self.history = data[-1000:] if len(data) > 1000 else data
            except Exception as e:
                logger.warning(f"Could not load job history: {e}")

        # Load job states
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self.job_states = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load job states: {e}")

    def _save_state(self):
        """Save state to files"""
        try:
            # Save history
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2, default=str)

            # Save states
            with open(self.state_file, "w") as f:
                json.dump(self.job_states, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Could not save state: {e}")

    def record_run(self, run: JobRun):
        """Record a job run"""
        self.history.append(run.to_dict())

        # Update job state
        self.job_states[run.job_name] = {
            "last_run": run.started_at.isoformat(),
            "last_success": run.success,
            "last_error": run.error
        }

        self._save_state()

    def get_last_run(self, job_name: str) -> Optional[datetime]:
        """Get the last run time for a job"""
        state = self.job_states.get(job_name)
        if state and state.get("last_run"):
            return datetime.fromisoformat(state["last_run"])
        return None

    def get_job_stats(self, job_name: str) -> Dict[str, Any]:
        """Get statistics for a specific job"""
        job_runs = [r for r in self.history if r.get("job_name") == job_name]

        if not job_runs:
            return {"total_runs": 0}

        successes = sum(1 for r in job_runs if r.get("success"))

        return {
            "total_runs": len(job_runs),
            "successes": successes,
            "failures": len(job_runs) - successes,
            "success_rate": round(successes / len(job_runs) * 100, 2),
            "last_run": job_runs[-1].get("started_at") if job_runs else None
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        job_names = set(r.get("job_name") for r in self.history)

        return {
            "total_runs": len(self.history),
            "jobs": {name: self.get_job_stats(name) for name in job_names}
        }

    def get_recent_runs(self, limit: int = 20) -> List[Dict]:
        """Get recent job runs"""
        return self.history[-limit:]

    def clear_history(self):
        """Clear job history"""
        self.history = []
        self._save_state()
        logger.info("Job history cleared")
