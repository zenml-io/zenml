"""Print the recent version history of the monitoring report artifact."""

from models import MonitoringReport

from zenml.client import Client


def main() -> None:
    """Load and summarize recent report artifact versions."""
    versions = Client().list_artifact_versions(
        name="web_monitoring_report", sort_by="desc:created", size=10
    )
    if not versions:
        print("No monitoring reports found. Run `python run.py` first.")
        return

    for version in versions:
        report: MonitoringReport = version.load()
        print(
            f"v{version.version}: {report.status} | "
            f"meaningful={report.analysis.meaningful} | {report.url}"
        )
        print(f"  {report.analysis.summary}")


if __name__ == "__main__":
    main()
