from kedro.pipeline import Pipeline, node, pipeline
from .nodes import graphical_soundscape_pamflow


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(  # Log
                func=graphical_soundscape_pamflow,
                inputs=["media@pamDP", "params:graphical_soundscape_parameters"],
                outputs=["graphical_soundscape@PartitionedDataset", "graph_plot@PartitionedImage"],
                name="graphical_soundscape_node",
            ),
        ]
    )
