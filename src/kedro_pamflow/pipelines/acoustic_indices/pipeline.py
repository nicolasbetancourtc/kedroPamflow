from kedro.pipeline import Pipeline, node, pipeline
from .nodes import compute_indices


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(  # Log
                func=compute_indices,
                inputs=["media@pamDP", "params:acoustic_indices"],
                outputs="acoustic_indices@PartitionedDataset",
                name="compute_indices_node",
            )
        ]
    )
