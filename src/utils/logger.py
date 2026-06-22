"""
Structured logging for Clinical ETL Platform.
"""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path


def get_logger(name: str, log_file: str = None) -> logging.Logger:
    """Get a configured logger with both console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


class PipelineMetricsLogger:
    """Records pipeline run metrics to JSON for proof/reporting."""

    def __init__(self, run_id: str, output_dir: str = "./outputs"):
        self.run_id = run_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = {
            "run_id": run_id,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "status": "RUNNING",
            "source_metrics": {},
            "quality_metrics": {},
            "performance_metrics": {},
            "errors": []
        }

    def log_source(self, source: str, records_extracted: int, duration_sec: float):
        self.metrics["source_metrics"][source] = {
            "records_extracted": records_extracted,
            "duration_sec": round(duration_sec, 2),
            "throughput_rps": round(records_extracted / max(duration_sec, 0.001), 0)
        }

    def log_quality(self, source: str, total: int, passed: int, failed: int):
        quality_score = passed / max(total, 1)
        self.metrics["quality_metrics"][source] = {
            "total_records": total,
            "passed": passed,
            "failed": failed,
            "quality_score": round(quality_score, 4),
            "quality_pct": f"{quality_score*100:.2f}%"
        }

    def log_performance(self, key: str, value):
        self.metrics["performance_metrics"][key] = value

    def finalize(self, status: str = "SUCCESS"):
        self.metrics["end_time"] = datetime.utcnow().isoformat()
        self.metrics["status"] = status

        # Compute overall quality
        if self.metrics["quality_metrics"]:
            scores = [m["quality_score"] for m in self.metrics["quality_metrics"].values()]
            self.metrics["overall_quality_score"] = round(sum(scores) / len(scores), 4)

        path = self.output_dir / f"pipeline_run_{self.run_id}.json"
        with open(path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        return path
