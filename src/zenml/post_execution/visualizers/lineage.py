import json

import pandas as pd
import plotly.express as px

from zenml.core.repo import Repository

steps_to_artifacts = {
    "datasource": ["DataGen", "DataSchema", "DataStatistics"],
    "preprocesser": ["Transform"],
    "sequencer": ["Sequencer", "SequencerStatistics", "SequencerSchema"],
    "split": ["SplitGen", "SplitStatistics", "SplitSchema"],
    "ImageGen": ["ImageGen"],
}

artifact_types = ["output"]


def read_lineage_info(repo: Repository):
    store = repo.get_active_stack().metadata_store
    pipelines = repo.get_pipelines()

    result = []

    for p in pipelines:
        # Get the config and status of the pipeline
        steps_config = p.get_steps_config()["steps"]
        components_status = store.get_components_status(p)

        # Handle datasource
        for a_type in artifact_types:
            s = "datasource"
            for component in steps_to_artifacts[s]:
                artifacts = store.get_artifacts_by_component_and_type(
                    p, component, a_type
                )
                e = store.get_execution_by_component(p, component)[0]
                for a in artifacts:
                    result.append(
                        {
                            "pipeline": p.name,
                            "step": s,
                            "status": "committed",
                            "source": p.datasource._source,
                            "args": p.datasource._source_args,
                            "artifact": store.store.get_artifact_types_by_id(
                                [a.type_id]
                            )[0].name,
                            "artifact_type": a_type,
                            "artifact_uri": a.uri,
                            "artifact_id": a.id,
                            "execution_id": e.id,
                        }
                    )

            # Handle steps
            for s, config in steps_config.items():
                for component in steps_to_artifacts[s]:
                    artifacts = store.get_artifacts_by_component_and_type(
                        p, component, a_type
                    )
                    e = store.get_execution_by_component(p, component)[0]
                    for a in artifacts:
                        result.append(
                            {
                                "pipeline": p.name,
                                "step": s,
                                "status": components_status[component],
                                "source": config["source"],
                                "args": config["args"],
                                "artifact": store.store.get_artifact_types_by_id(
                                    [a.type_id]
                                )[
                                    0
                                ].name,
                                "artifact_type": a_type,
                                "artifact_uri": a.uri,
                                "artifact_id": a.id,
                                "execution_id": e.id,
                            }
                        )

            # Handle additional components
            extra_components = ["ImageGen"]
            for s in extra_components:
                for component in steps_to_artifacts[s]:
                    artifacts = store.get_artifacts_by_component_and_type(
                        p, component, a_type
                    )
                    e = store.get_execution_by_component(p, component)[0]
                    for a in artifacts:
                        result.append(
                            {
                                "pipeline": p.name,
                                "step": s,
                                "status": components_status[s],
                                "source": f"zenml@{component}",
                                "args": "",
                                "artifact": store.store.get_artifact_types_by_id(
                                    [a.type_id]
                                )[
                                    0
                                ].name,
                                "artifact_type": a_type,
                                "artifact_uri": a.uri,
                                "artifact_id": a.id,
                                "execution_id": e.id,
                            }
                        )

    return result


def artifact_lineage_graph(repo: Repository):
    result_df = pd.DataFrame(read_lineage_info(repo))

    fig = px.treemap(
        result_df,
        path=["pipeline", "step", "artifact"],
        hover_data={
            "source": True,
            "args": True,
        },
        color="status",
        color_discrete_map={
            "(?)": "purple",
            "committed": "orange",
            "complete": "green",
            "cached": "lightgreen",
        },
    )
    fig.update_annotations(hoverinfo="skip")

    return fig


def pipeline_lineage_graph(repo: Repository):
    category_df = {}

    for step_artifact in read_lineage_info(repo):
        pipeline = step_artifact["pipeline"]
        step = step_artifact["step"]

        if pipeline not in category_df:
            category_df[pipeline] = {"pipeline": pipeline}

        category_df[pipeline].update(
            {
                f"{step}_status": step_artifact["status"],
                f"{step}_source": step_artifact["source"]
                .split("@")[0]
                .split(".")[-1],
                f"{step}_args": step_artifact["args"],
            }
        )

        if f"{step}_artifact_ids" not in category_df[pipeline]:
            category_df[pipeline][f"{step}_artifact_ids"] = set()

        category_df[pipeline][f"{step}_artifact_ids"].add(
            step_artifact["artifact_id"]
        )

    for pipeline in category_df:
        for step in steps_to_artifacts:
            source = category_df[pipeline][f"{step}_source"]
            output_artifacts = json.dumps(
                sorted(category_df[pipeline][f"{step}_artifact_ids"])
            )

            category_df[pipeline][step] = f"{source}-{output_artifacts}"

    category_df = pd.DataFrame.from_dict(category_df, "index")

    category_df = category_df.reset_index()

    fig = px.parallel_categories(
        category_df,
        dimensions=[
            "pipeline",
            "datasource",
            "sequencer",
            "split",
            "preprocesser",
            "ImageGen",
        ],
        color=category_df.index,
        labels="status",
    )

    return fig


repo = Repository()
artifact_lineage_graph(repo)
