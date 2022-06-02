def build_base_pod_manifest(
    run_name,
    pipeline_name,
    image_name,
):
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": None,  # to be set in update_pod_manifest
            "labels": {
                "run": run_name,
                "pipeline": pipeline_name,
            },
        },
        "spec": {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": "main",
                    "image": image_name,
                    "command": None,  # to be set in update_pod_manifest
                    "args": None,  # to be set in update_pod_manifest
                }
            ],
        },
    }


def update_pod_manifest(base_pod_manifest, pod_name, command, args):
    pod_manifest = base_pod_manifest.copy()
    pod_manifest["metadata"]["name"] = pod_name
    pod_manifest["spec"]["containers"][0]["command"] = command
    pod_manifest["spec"]["containers"][0]["args"] = args
    return pod_manifest
