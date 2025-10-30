# Computer Vision Object Detection with ZenML

Build production-ready computer vision pipelines with ZenML, Ultralytics YOLO, and FiftyOne. This example demonstrates:

- 🎯 **Training Pipeline**: Load COCO dataset and train a YOLO model
- 🚀 **Inference Pipeline**: Deploy as a real-time HTTP service with warm model loading
- 🖼️ **Web Interface**: Interactive UI for testing object detection
- 📊 **FiftyOne Integration**: Dataset visualization and management
- 🔄 **Full Lineage**: Track all artifacts, datasets, and model versions

## 🎬 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize ZenML (if not already done)
zenml init
zenml login  # Optional: connect to ZenML Cloud or deployed server
```

### 1️⃣ Train a Model

Train a YOLOv8 nano model on a subset of the COCO dataset:

```bash
python run.py --train --samples 50 --epochs 3
```

This will:
- Download 50 images from COCO validation set using FiftyOne
- Train a YOLOv8n model for 3 epochs
- Create visualizations with FiftyOne
- Save the trained model as a ZenML artifact

**Output:**
```
Training YOLO Object Detection Model
=====================================
Dataset: COCO validation subset (50 samples)
Model: yolov8n.pt
Epochs: 3
=====================================
...
✅ Training Complete!
Model artifact ID: abc-123-def-456
```

### 2️⃣ Test Inference Locally

Run object detection on an image in batch mode:

```bash
# Test with a URL
python run.py --predict --image https://ultralytics.com/images/bus.jpg

# Test with a local file
python run.py --predict --image path/to/your/image.jpg

# Adjust confidence threshold
python run.py --predict --image https://ultralytics.com/images/bus.jpg --confidence 0.5
```

**Output:**
```
🎯 Detection Results
====================
Objects detected: 4
Image size: 640 x 480

📦 Detected Objects:
  1. bus (confidence: 89.23%)
     BBox: [50, 100, 500, 400]
  2. person (confidence: 76.45%)
     BBox: [200, 150, 250, 350]
  ...
```

### 3️⃣ Deploy as HTTP Service

Deploy the inference pipeline as a real-time HTTP service:

```bash
zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline
```

This creates a long-running service with:
- ⚡ **Warm model loading**: Model loaded once at startup for fast inference
- 🌐 **HTTP API**: RESTful endpoint for predictions
- 🖼️ **Web UI**: Interactive interface at `http://localhost:8000`
- 📊 **Full tracking**: All predictions tracked as ZenML artifacts

### 4️⃣ Use the Deployed Service

#### Interactive Web UI

Open your browser to `http://localhost:8000`:

1. Enter an image URL (or upload a local file in future versions)
2. Adjust confidence threshold
3. Click "Detect Objects"
4. View results with bounding boxes and labels

#### REST API

Call the API programmatically:

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "image_path": "https://ultralytics.com/images/bus.jpg",
      "confidence_threshold": 0.25
    }
  }'
```

**Response:**
```json
{
  "detections": [
    {
      "bbox": [50.2, 100.5, 500.8, 400.3],
      "label": "bus",
      "confidence": 0.8923,
      "class_id": 5
    },
    {
      "bbox": [200.1, 150.2, 250.5, 350.8],
      "label": "person",
      "confidence": 0.7645,
      "class_id": 0
    }
  ],
  "num_detections": 2,
  "annotated_image_path": "/path/to/annotated_image.jpg",
  "image_size": {"width": 640, "height": 480},
  "model_version": "1.0.0"
}
```

#### ZenML Dashboard Playground

The ZenML dashboard includes a built-in playground for testing deployed pipelines:

1. Navigate to your deployment in the dashboard
2. Fill in the input parameters interactively
3. Send requests and see real-time results
4. Share working examples with your team

## 📁 Project Structure

```
computer_vision/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── run.py                            # CLI entry point
├── pipelines/
│   ├── __init__.py
│   ├── training_pipeline.py          # Train YOLO on COCO dataset
│   ├── inference_pipeline.py         # Deployable inference service
│   └── hooks.py                      # Warm model loading hooks
├── steps/
│   ├── __init__.py
│   ├── data_loader.py                # Load COCO with FiftyOne
│   ├── model_trainer.py              # Train YOLO model
│   ├── evaluate.py                   # Evaluate model performance
│   └── inference.py                  # Run object detection
├── materializers/
│   ├── __init__.py
│   └── ultralytics_materializer.py   # Custom YOLO model materializer
└── ui/
    └── index.html                     # Interactive web interface
```

## 🔑 Key Concepts

### Pipeline Deployments

ZenML allows you to deploy pipelines as real-time HTTP services. Just add `DeploymentSettings` to your pipeline:

```python
from zenml import pipeline
from zenml.config import DeploymentSettings, CORSConfig

@pipeline(
    settings={
        "deployment": DeploymentSettings(
            app_title="YOLO Object Detection Service",
            dashboard_files_path="ui",  # Serve web UI
            cors=CORSConfig(allow_origins=["*"]),
        ),
    }
)
def object_detection_inference_pipeline(image_path: str) -> dict:
    return run_detection(image_path)
```

Deploy with: `zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline`

### Warm Container Pattern

The `on_init` hook loads the model once at deployment startup, keeping it warm in memory for all requests:

```python
@pipeline(
    on_init=init_model,        # Load model at startup
    on_cleanup=cleanup_model,  # Clean shutdown
)
def object_detection_inference_pipeline(image_path: str) -> dict:
    return run_detection(image_path)
```

This eliminates cold-start delays and provides sub-second inference times.

### Artifacts and Materializers

ZenML automatically tracks all data flowing through your pipelines:

- **Datasets**: Dataset paths (directories) stored with built-in `PathMaterializer`
- **Images**: Using PathMaterializer to handle image directories
- **Models**: YOLO model weights tracked as versioned artifacts
- **Predictions**: Detection results stored for reproducibility

Example from training pipeline:

```python
@step
def train_yolo_model(
    dataset_path: Path,
    epochs: int = 3,
) -> Annotated[Path, "model_path"]:
    """Train YOLO and return model path as a tracked artifact."""
    model = YOLO("yolov8n.pt")
    results = model.train(data=str(dataset_path), epochs=epochs)
    return Path("runs/detect/coco_training/weights/best.pt")
```

ZenML automatically:
- Stores the model file in the artifact store
- Versions it with the pipeline run
- Makes it available for loading in other pipelines

### FiftyOne Integration

FiftyOne provides powerful dataset management and visualization:

```python
@step
def load_coco_dataset(max_samples: int = 50) -> Tuple[Path, str]:
    """Load COCO dataset using FiftyOne."""
    dataset = foz.load_zoo_dataset(
        "coco-2017",
        split="validation",
        max_samples=max_samples,
    )
    # Export to YOLO format
    dataset.export(export_dir="data/coco", dataset_type=fo.types.YOLOv5Dataset)
    return Path("data/coco"), dataset.name
```

View the dataset in FiftyOne App:

```bash
python -c "import fiftyone as fo; fo.launch_app(fo.load_dataset('coco-2017-detection-subset'))"
```

## 🎨 Customization

### Use a Different Dataset

Replace the COCO loader with your own dataset:

```python
@step
def load_custom_dataset() -> Path:
    """Load your custom dataset in YOLO format."""
    # Your dataset should have this structure:
    # dataset/
    #   ├── images/
    #   │   └── train/
    #   ├── labels/
    #   │   └── train/
    #   └── data.yaml
    return Path("path/to/your/dataset")
```

### Use a Larger Model

For better accuracy, use a larger YOLO model:

```bash
python run.py --train --model yolov8m.pt --epochs 10
```

Available models: `yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`, `yolov8l.pt`, `yolov8x.pt`

### Add Custom Post-Processing

Extend the inference step with custom logic:

```python
@step
def run_detection_with_tracking(
    image_path: str,
    confidence_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Run detection with object tracking."""
    results = run_detection(image_path, confidence_threshold)
    
    # Add your custom logic here
    # e.g., object tracking, filtering, aggregation
    
    return results
```

### Deploy to Cloud

Use ZenML's cloud deployers to deploy to AWS, GCP, or Azure:

```bash
# AWS App Runner
zenml deployer register aws --flavor=aws-app-runner --region=us-east-1
zenml stack update -d aws

# GCP Cloud Run
zenml deployer register gcp --flavor=gcp-cloud-run --project=my-project
zenml stack update -d gcp

# Then deploy as usual
zenml pipeline deploy pipelines.inference_pipeline.object_detection_inference_pipeline
```

## 🔧 Advanced Usage

### Batch Processing

Process multiple images in a batch:

```python
@pipeline
def batch_detection_pipeline(image_dir: str) -> List[Dict]:
    """Process all images in a directory."""
    images = list_images(image_dir)
    results = []
    for image_path in images:
        result = run_detection(image_path)
        results.append(result)
    return results
```

### Model Comparison

Compare different YOLO models:

```bash
# Train multiple models
python run.py --train --model yolov8n.pt --epochs 3
python run.py --train --model yolov8s.pt --epochs 3

# Compare in ZenML dashboard
# Navigate to Artifacts → yolo-model → Compare Versions
```

### A/B Testing

Deploy multiple model versions and route traffic:

```python
@step
def run_ab_test(image_path: str) -> Dict:
    """Run A/B test between model versions."""
    import random
    
    # Load two model versions
    model_a = Client().get_artifact_version("yolo-model", "1.0.0").load()
    model_b = Client().get_artifact_version("yolo-model", "2.0.0").load()
    
    # Route 50/50
    model = model_a if random.random() < 0.5 else model_b
    return run_detection_with_model(image_path, model)
```

## 📊 Monitoring and Debugging

### View Pipeline Runs

```bash
# List all runs
zenml pipeline runs list

# Get details of a specific run
zenml pipeline runs describe <run-id>

# View artifacts produced
zenml artifact list --pipeline-name object_detection_training_pipeline
```

### Check Deployment Status

```bash
# List deployments
zenml deployment list

# Get deployment details
zenml deployment describe object_detection_inference_pipeline

# View deployment logs
zenml deployment logs object_detection_inference_pipeline
```

### Visualize with FiftyOne

View your training data and predictions in FiftyOne:

```python
import fiftyone as fo

# Load the training dataset
dataset = fo.load_dataset("coco-2017-detection-subset")

# Launch the FiftyOne app
session = fo.launch_app(dataset)
```

## 🐛 Troubleshooting

### Model Not Found Error

If you see "No production model found":

1. Make sure you've trained a model: `python run.py --train`
2. The model is automatically tagged as 'production' during training
3. Verify the artifact exists: `zenml artifact list --name yolo-model --tag production`

### Image Not Found Error

The deployed pipeline requires image paths that are accessible:

- ✅ **URLs**: `https://example.com/image.jpg`
- ✅ **Absolute paths**: `/home/user/images/photo.jpg`
- ❌ **Relative paths**: `./images/photo.jpg` (may not work in deployment)

### FiftyOne Dataset Errors

If FiftyOne datasets are not persisting:

```bash
# Check FiftyOne database
fiftyone datasets list

# Delete and recreate if needed
fiftyone datasets delete coco-2017-detection-subset
python run.py --train
```

### Deployment Port Already in Use

If port 8000 is already in use, modify the deployment settings:

```python
DeploymentSettings(
    uvicorn_port=8001,  # Use a different port
    ...
)
```

## 📚 Learn More

- [ZenML Documentation](https://docs.zenml.io/)
- [Pipeline Deployments Guide](https://docs.zenml.io/how-to/deployment/deployment)
- [Deployment Settings](https://docs.zenml.io/how-to/deployment/deployment_settings)
- [Artifacts and Materializers](https://docs.zenml.io/how-to/artifacts)
- [Ultralytics Documentation](https://docs.ultralytics.com/)
- [FiftyOne Documentation](https://docs.voxel51.com/)

## 🤝 Related Examples

- **Quickstart**: [examples/quickstart](../quickstart) - Basic ZenML pipeline
- **Deploying ML Models**: [examples/deploying_ml_model](../deploying_ml_model) - Classical ML deployment
- **E2E Example**: [examples/e2e](../e2e) - End-to-end ML workflow

## 💡 Tips

1. **Start small**: Begin with 50 samples and 3 epochs to test the pipeline quickly
2. **Use pretrained models**: YOLO models are pretrained on COCO, so even 3 epochs shows results
3. **Monitor resources**: Object detection can be memory-intensive, adjust `ResourceSettings` if needed
4. **Cache wisely**: Disable caching in inference pipeline to always use latest inputs
5. **Version everything**: Use ZenML's tagging to track production models

---

Built with ❤️ using [ZenML](https://zenml.io), [Ultralytics](https://ultralytics.com), and [FiftyOne](https://voxel51.com/fiftyone)

