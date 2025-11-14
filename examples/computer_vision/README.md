# Train and deploy YOLO Object Detection with ZenML, Ultralytics, and FiftyOne

Learn how to build a production-ready computer vision pipeline with YOLOv8, FiftyOne dataset management, and deploy it as a warm HTTP service with an interactive web interface. This example showcases the complete **FiftyOne annotation workflow loop**: export → train → predict → import → analyze → visualize.

## 🎯 What You'll Build

![Interactive Web UI](assets/app.png)

- **Complete FiftyOne Annotation Workflow**: Export COCO data → Train YOLO → Run inference on original FiftyOne dataset → Import predictions back → Analyze performance → Interactive dashboard visualization
- **Production-Ready Training**: YOLOv8 model training with automatic artifact versioning and performance tracking via ZenML
- **Real-Time Inference Service**: Deploy as warm HTTP service with sub-second latency using ZenML's deployment system
- **Interactive Web UI**: Upload images or use URLs for instant object detection testing with visual results
- **Dataset-Model Lineage**: Full traceability linking FiftyOne datasets to ZenML model artifacts and predictions
- **Visual Performance Analysis**: Side-by-side comparison of predictions vs ground truth in FiftyOne's interactive dashboard

## 🏃 Quickstart

```bash
pip install -r requirements.txt
zenml init
zenml login
```

**Train with FiftyOne analysis** ([see code](pipelines/training_pipeline.py)):

```bash
# Full workflow: training + FiftyOne analysis
python run.py --train --samples 50 --epochs 3

# Fast training (skip FiftyOne analysis)
python run.py --train --samples 50 --epochs 3 --disable-fiftyone-analysis
```

This downloads 50 COCO validation images via FiftyOne, trains a YOLOv8 nano model for 3 epochs, runs inference on the original FiftyOne dataset, and provides interactive analysis capabilities.

**Deploy as a real-time service** ([see code](pipelines/inference_pipeline.py)):

```bash
zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline
```

Visit `http://localhost:8000` for the interactive UI ([see code](ui/index.html)).

**Test batch inference locally**:

The inference step supports multiple image input formats:

```bash
# Using image URL
python run.py --predict --image https://ultralytics.com/images/bus.jpg

# Using local file path
python run.py --predict --image /path/to/local/image.jpg

# Using base64 data URI (useful for programmatic usage)
python run.py --predict --image "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA..."
```

**Make predictions via API**:

```bash
# Using image URL
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "image_path": "https://ultralytics.com/images/bus.jpg",
      "confidence_threshold": 0.25
    }
  }'
```

**Explore with FiftyOne Dashboard**:

![FiftyOne dashboard](assets/fiftyone_dashboard.png)

After training, the pipeline creates persistent FiftyOne datasets linked to your ZenML model artifacts. Launch the dashboard to analyze results:

```bash
# Easy way - automatically finds datasets with predictions
python launch_fiftyone.py

# Launch specific dataset with custom port
python launch_fiftyone.py coco-2017-validation-50samples --port 8080

# Manual way
fiftyone app launch
# Then in Python: fo.load_dataset('coco-2017-validation-50samples')
```

**Dataset-Artifact Connection**: Each FiftyOne dataset (named by parameters like `coco-2017-validation-50samples`) stores predictions from your ZenML runs. Re-running pipelines now creates a new versioned predictions field (e.g., `predictions_v8_a1b2c3d4`) and updates the stable `predictions` alias to point to the latest, preserving all prior versions for comparison. See the "Versioned Predictions and ZenML Lineage Tracking" section below for details.

In the FiftyOne dashboard you can:
- Compare predictions vs ground truth side-by-side
- Filter by confidence levels and object classes
- Analyze per-class performance metrics
- Identify false positives and negatives
- Export problematic samples for retraining

**Use the ZenML Deployment Playground**

The ZenML dashboard includes a built-in playground for deployed pipelines, allowing you to test your service directly from the UI. Navigate to your deployment in the dashboard, fill in the image URL and confidence threshold, and see real-time detection results with visualizations.

## 🏗️ What's Inside

```
computer_vision/
├── pipelines/
│   ├── training_pipeline.py      - Train YOLO + optional FiftyOne analysis
│   ├── inference_pipeline.py     - Real-time detection service
│   └── hooks.py                  - Warm model loading at startup/shutdown
├── steps/
│   ├── data_loader.py            - COCO dataset loading via FiftyOne
│   ├── model_trainer.py          - YOLO model training
│   ├── evaluate.py               - Model evaluation metrics
│   ├── inference.py              - Fast object detection (supports base64 uploads)
│   └── fiftyone_analysis.py      - Complete annotation workflow loop
├── annotators/
│   ├── __init__.py               - Annotator package initialization
│   └── fiftyone_annotator.py     - FiftyOne annotator class (ZenML-style)
├── materializers/
│   └── ultralytics_materializer.py  - Custom YOLO model serialization
├── ui/
│   └── index.html                - Interactive web interface with image upload
├── run.py                        - CLI for training and testing
├── launch_fiftyone.py            - Easy FiftyOne dashboard launcher (uses annotator)
└── requirements.txt              - Dependencies
```

## 🔑 Important Notes

### **FiftyOne Annotator Class**

This example includes a `FiftyOneAnnotator` class that encapsulates all FiftyOne functionality in a clean, ZenML-style interface.

- 📄 [View FiftyOne annotator documentation](./annotators/README.md)
- 🔧 [View annotator implementation](./annotators/fiftyone_annotator.py)
- 🎯 **Key fix**: Proper COCO 80-class mapping ensures successful training (mAP@50: 0.799) vs broken training (0 mAP)

### **Custom Materializers**

This example features a [custom ZenML materializer](https://docs.zenml.io/how-to/types-and-materializers/materializers) for YOLO models that handles model weight serialization and artifact versioning, ensuring seamless model tracking across pipeline runs. ZenML automatically manages and version-controls model artifacts, making them accessible throughout your pipeline lifecycle.

- 📖 [ZenML Materializers Documentation](https://docs.zenml.io/concepts/artifacts/materializers)
- 📄 [View YOLO model materializer code](./materializers/ultralytics_materializer.py)

### **Versioned Predictions and ZenML Lineage Tracking**

Predictions are versioned. Every inference run writes to a new field on your FiftyOne dataset (for example, `predictions_v8_a1b2c3d4`) so you can compare model versions, track changes over time, and never lose history. For backwards compatibility, a stable `predictions` alias mirrors the latest version.

Why this matters:
- Compare different model versions side-by-side in the FiftyOne App
- Track how performance changes across runs and parameter tweaks
- Preserve a complete history of your predictions for auditability

How it works:
- Versioned fields:
  - Each run writes predictions to a unique field named `predictions_{suffix}`
  - Suffix scheme is timestamp + short UUID by default (e.g., `20250310T134501Z_1a2b3c4d`)
  - If ZenML context is available, a human-friendly suffix is used (e.g., `v{model_version}_{run_id[:8]}`)
- Latest field pointer:
  - The dataset stores the current "latest" field in `dataset.info["latest_predictions_field"]`
  - The stable `predictions` alias mirrors the latest field for existing code
- Full lineage metadata:
  - Each prediction version appends a record to `dataset.info["prediction_versions"]` with creation time, parameters, model info, and ZenML lineage

ZenML lineage captured per version includes:
- Pipeline run ID and name
- Step run ID and name
- Model artifact information (name/version; class list if available)
- Parameters used (e.g., confidence threshold)
- UTC timestamps

Inspecting metadata:
```python
import fiftyone as fo

# Load dataset and inspect versions
ds = fo.load_dataset("coco-2017-validation-50samples")

# View all prediction versions
versions = ds.info.get("prediction_versions", [])
for v in versions:
    print(f"Field: {v['field']}")
    print(f"Created: {v['created_at']}")
    print(f"ZenML Run: {v['zenml']['pipeline_run_id']}")
    print(f"Model: {v['model']['name']} v{v['model']['version']}")
    print()

# Get latest field
latest = ds.info.get("latest_predictions_field")
print(f"Latest predictions: {latest}")
```

Comparing versions in FiftyOne:
- Open the FiftyOne App and use the left sidebar field selector to switch between prediction fields (e.g., `predictions_v8_a1b2c3d4`, `predictions_20250310T134501Z_1a2b3c4d`)
- Evaluate, filter, and visualize each field to compare performance across runs

Backward compatibility:
- Existing code that reads from `predictions` continues to work
- The `predictions` alias always mirrors the latest version so dashboards and scripts remain compatible

### 🎨 Customization

**Use a different dataset**: To use your own dataset (in YOLO format), modify the dataset loading logic in [`run.py`](./run.py) and/or the relevant pipeline step (e.g., `load_coco_dataset` in [`steps/data_loader.py`](./steps/data_loader.py)) to point to your images, labels, and `data.yaml`.

**Use a larger model**: For better accuracy, use `yolov8s.pt`, `yolov8m.pt`, `yolov8l.pt`, or `yolov8x.pt`:

```bash
python run.py --train --model yolov8m.pt --epochs 10
```

**Run training on cloud**: Use ZenML's remote orchestrators for scalable training:

```bash
# Kubernetes orchestrator
zenml orchestrator register k8s --flavor=kubernetes
zenml stack update -o k8s

# Then run training remotely
python run.py --train --samples 500 --epochs 20 --model yolov8m.pt
```

**Deploy inference to cloud**: Use ZenML's cloud deployers:

```bash
# AWS App Runner
zenml deployer register aws --flavor=aws-app-runner --region=us-east-1
zenml stack update -d aws
zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline
```

## 📚 Learn More

- [Pipeline Deployments Guide](https://docs.zenml.io/how-to/deployment/deployment)
- [Deployment Settings](https://docs.zenml.io/how-to/deployment/deployment_settings)
- [Pipeline Hooks](https://docs.zenml.io/how-to/steps-pipelines/advanced_features#pipeline-and-step-hooks)
- [Ultralytics Documentation](https://docs.ultralytics.com/)
- [FiftyOne Documentation](https://docs.voxel51.com/)
- [Related Example: Deploying ML Models](../deploying_ml_model/README.md)
